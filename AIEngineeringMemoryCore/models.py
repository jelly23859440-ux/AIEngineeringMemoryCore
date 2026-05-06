import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, List, Literal
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


ConfidenceLevel = Literal["high", "medium", "low", "manual_corrected"]


class EntityRecord(BaseModel):
    model_config = {"use_enum_values": True}

    entity_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_name: str
    entity_type: str
    exact_value: Any
    confidence: ConfidenceLevel = "medium"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_episode_id: Optional[str] = None

    @field_validator("entity_name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("entity_name must not be empty")
        return v.strip()


class EpisodeSummary(BaseModel):
    model_config = {"use_enum_values": True}

    episode_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    summary_text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: ConfidenceLevel = "medium"
    related_entity_ids: List[str] = Field(default_factory=list)
    is_cold: bool = False
    trigger_keywords: List[str] = Field(default_factory=list)
    token_count: int = 0

    @field_validator("summary_text")
    @classmethod
    def summary_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("summary_text must not be empty")
        return v.strip()


class MemoryPacket(BaseModel):
    packet_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    episodes: List[EpisodeSummary] = Field(default_factory=list)
    entities: List[EntityRecord] = Field(default_factory=list)
    source_task_id: Optional[str] = None


class HeartbeatState(BaseModel):
    total_tokens: int = 0
    context_limit: int = 4096
    heartbeat_ratio: float = 0.8
    last_heartbeat_at: Optional[datetime] = None
    is_consolidating: bool = False

    @property
    def threshold(self) -> int:
        return int(self.context_limit * self.heartbeat_ratio)

    @property
    def should_consolidate(self) -> bool:
        return self.total_tokens >= self.threshold and not self.is_consolidating


def packet_to_json(packet: MemoryPacket) -> str:
    return packet.model_dump_json(indent=2, ensure_ascii=False)


def json_to_packet(json_str: str) -> MemoryPacket:
    return MemoryPacket.model_validate_json(json_str)


def packet_to_file(packet: MemoryPacket, filepath: Path) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(packet_to_json(packet), encoding="utf-8")


def file_to_packet(filepath: Path) -> MemoryPacket:
    return json_to_packet(filepath.read_text(encoding="utf-8"))


def heartbeat_state_to_json(state: HeartbeatState) -> str:
    return state.model_dump_json(indent=2, ensure_ascii=False)


def json_to_heartbeat_state(json_str: str) -> HeartbeatState:
    return HeartbeatState.model_validate_json(json_str)


def heartbeat_state_to_file(state: HeartbeatState, filepath: Path) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(heartbeat_state_to_json(state), encoding="utf-8")


def file_to_heartbeat_state(filepath: Path) -> HeartbeatState:
    return json_to_heartbeat_state(filepath.read_text(encoding="utf-8"))
