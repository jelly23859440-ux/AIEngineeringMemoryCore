import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import portalocker
import tiktoken

from models import HeartbeatState, heartbeat_state_to_json, json_to_heartbeat_state


DEFAULT_ENCODING = "cl100k_base"


class HeartbeatMonitor:
    def __init__(
        self,
        context_limit: int = 4096,
        heartbeat_ratio: float = 0.8,
        state_path: Optional[Path] = None,
        encoding_name: str = DEFAULT_ENCODING,
    ):
        self.context_limit = context_limit
        self.heartbeat_ratio = heartbeat_ratio
        self.state_path = state_path
        self.encoding_name = encoding_name
        self._encoding: Optional[tiktoken.Encoding] = None
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[], None]] = []

        self._state = HeartbeatState(
            context_limit=context_limit,
            heartbeat_ratio=heartbeat_ratio,
        )

        if self.state_path and self.state_path.exists():
            self._load_state()
        else:
            self._state.context_limit = context_limit
            self._state.heartbeat_ratio = heartbeat_ratio

    @property
    def encoding(self) -> tiktoken.Encoding:
        if self._encoding is None:
            self._encoding = tiktoken.get_encoding(self.encoding_name)
        return self._encoding

    @property
    def total_tokens(self) -> int:
        return self._state.total_tokens

    @property
    def is_consolidating(self) -> bool:
        return self._state.is_consolidating

    def track_message(self, text: str) -> int:
        token_count = len(self.encoding.encode(text))
        with self._lock:
            self._state.total_tokens += token_count
            should_trigger = self._state.should_consolidate
            if should_trigger:
                self._state.is_consolidating = True
                self._state.last_heartbeat_at = datetime.now(timezone.utc)

        if self.state_path:
            self._save_state()

        if should_trigger:
            self._fire_callbacks()

        return token_count

    def register_callback(self, callback: Callable[[], None]) -> None:
        self._callbacks.append(callback)

    def reset(self) -> None:
        with self._lock:
            self._state.total_tokens = 0
            self._state.is_consolidating = False

        if self.state_path:
            self._save_state()

    def force_consolidate(self) -> None:
        with self._lock:
            self._state.is_consolidating = True
            self._state.last_heartbeat_at = datetime.now(timezone.utc)

        if self.state_path:
            self._save_state()

        self._fire_callbacks()

    def set_consolidation_complete(self) -> None:
        with self._lock:
            self._state.is_consolidating = False

        if self.state_path:
            self._save_state()

    def _fire_callbacks(self) -> None:
        for callback in self._callbacks:
            try:
                callback()
            except Exception:
                pass

    def _save_state(self) -> None:
        if not self.state_path:
            return
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            json_str = heartbeat_state_to_json(self._state)
            with open(self.state_path, "w", encoding="utf-8") as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                try:
                    f.write(json_str)
                    f.flush()
                finally:
                    portalocker.unlock(f)
        except Exception:
            pass

    def _load_state(self) -> None:
        if not self.state_path or not self.state_path.exists():
            return
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                portalocker.lock(f, portalocker.LOCK_SH)
                try:
                    content = f.read()
                    self._state = json_to_heartbeat_state(content)
                finally:
                    portalocker.unlock(f)
        except Exception:
            pass
