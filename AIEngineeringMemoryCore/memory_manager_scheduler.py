import threading
import time
from collections import deque
from typing import Optional, List, Callable, Literal

from consolidator import Consolidator
from memory_retriever import MemoryRetriever
from cold_storage_manager import ColdStorageManager
from models import MemoryPacket


SchedulerMode = Literal["async", "realtime", "hybrid"]


class MemoryManagerScheduler:
    def __init__(
        self,
        mode: SchedulerMode = "hybrid",
        async_heartbeat_batch: int = 60,
        consolidator: Optional[Consolidator] = None,
        retriever: Optional[MemoryRetriever] = None,
        cold_manager: Optional[ColdStorageManager] = None,
    ):
        self.mode = mode
        self.async_heartbeat_batch = async_heartbeat_batch
        self.consolidator = consolidator
        self.retriever = retriever
        self.cold_manager = cold_manager

        self._pending_exchanges: deque[dict] = deque()
        self._pending_heartbeat_count: int = 0
        self._consolidated_packets: List[MemoryPacket] = []

        self._async_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._consolidation_event = threading.Event()
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stop_event.clear()

        if self.mode in ("async", "hybrid"):
            self._async_thread = threading.Thread(
                target=self._async_loop, daemon=True
            )
            self._async_thread.start()

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        self._consolidation_event.set()

        if self._async_thread and self._async_thread.is_alive():
            self._async_thread.join(timeout=5)

    def record_exchange(self, user_msg: str, ai_response: str) -> None:
        exchange = {
            "role": "user",
            "content": user_msg,
        }
        ai_exchange = {
            "role": "assistant",
            "content": ai_response,
        }

        with self._lock:
            self._pending_exchanges.append(exchange)
            self._pending_exchanges.append(ai_exchange)
            self._pending_heartbeat_count += 1

            if self.mode == "realtime":
                self._trigger_consolidation()

            if self.mode == "async" or self.mode == "hybrid":
                if self._pending_heartbeat_count >= self.async_heartbeat_batch:
                    self._consolidation_event.set()

    def pre_retrieve_hook(self) -> None:
        if self.mode == "realtime":
            self._trigger_consolidation()

    def emergency_consolidate(self) -> None:
        self._trigger_consolidation()

    def _trigger_consolidation(self) -> None:
        if not self.consolidator:
            return

        with self._lock:
            if not self._pending_exchanges:
                return
            exchanges = list(self._pending_exchanges)
            self._pending_exchanges.clear()
            self._pending_heartbeat_count = 0

        try:
            packet = self.consolidator.consolidate(exchanges)
            self._consolidated_packets.append(packet)

            if self.retriever:
                self.retriever.index_packet(packet)
        except Exception:
            pass

    def _async_loop(self) -> None:
        while self._running and not self._stop_event.is_set():
            self._consolidation_event.wait(timeout=5)
            if self._stop_event.is_set():
                break
            self._consolidation_event.clear()

            with self._lock:
                if self._pending_heartbeat_count >= self.async_heartbeat_batch:
                    exchanges = list(self._pending_exchanges)
                    self._pending_exchanges.clear()
                    self._pending_heartbeat_count = 0
                else:
                    continue

            if exchanges and self.consolidator:
                try:
                    packet = self.consolidator.consolidate(exchanges)
                    self._consolidated_packets.append(packet)
                    if self.retriever:
                        self.retriever.index_packet(packet)
                except Exception:
                    pass

    def get_consolidated_packets(self) -> List[MemoryPacket]:
        with self._lock:
            return list(self._consolidated_packets)
