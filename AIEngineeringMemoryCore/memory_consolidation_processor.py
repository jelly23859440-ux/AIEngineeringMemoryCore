import json
from datetime import datetime, timezone
from typing import List, Optional

from consolidator import Consolidator
from project_manager import ProjectManager
from models import MemoryPacket, EpisodeSummary, EntityRecord, packet_to_file, ConfidenceLevel


class MemoryConsolidationProcessor:
    def __init__(
        self,
        consolidator: Consolidator,
        project_manager: ProjectManager,
    ):
        self.consolidator = consolidator
        self.project_manager = project_manager

    def process(self, pending_memories: List[MemoryPacket]) -> MemoryPacket:
        if not pending_memories:
            return MemoryPacket()

        packets_json = json.dumps(
            [p.model_dump(mode="json") for p in pending_memories],
            ensure_ascii=False,
            indent=2,
        )

        self._backup_old_entries(pending_memories)

        result = self.consolidator.summarize_for_consolidation(packets_json)
        return result

    def _backup_old_entries(self, old_packets: List[MemoryPacket]) -> None:
        for i, packet in enumerate(old_packets):
            backup_name = f"backup_{packet.packet_id}_{i}.json"
            backup_path = self.project_manager.get_backup_path(backup_name)
            packet_to_file(packet, backup_path)

    def _writeback_confidence(
        self, entity: EntityRecord, new_confidence: ConfidenceLevel
    ) -> None:
        entity.confidence = new_confidence
        entity.updated_at = datetime.now(timezone.utc)

        entity_path = self.project_manager.get_entity_path(entity.entity_id)
        entity_path.parent.mkdir(parents=True, exist_ok=True)
        entity_path.write_text(
            entity.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def merge_packets(self, packets: List[MemoryPacket]) -> MemoryPacket:
        """Local merge without calling AI - fast dedup by entity name."""
        merged_episodes: List[EpisodeSummary] = []
        merged_entities: List[EntityRecord] = []
        seen_episode_texts: set[str] = set()
        seen_entity_keys: set[tuple] = set()

        for packet in packets:
            for ep in packet.episodes:
                key = ep.summary_text.strip().lower()
                if key not in seen_episode_texts:
                    seen_episode_texts.add(key)
                    merged_episodes.append(ep)

            for ent in packet.entities:
                key = (ent.entity_name.strip().lower(), ent.entity_type)
                if key not in seen_entity_keys:
                    seen_entity_keys.add(key)
                    merged_entities.append(ent)

        return MemoryPacket(
            episodes=merged_episodes,
            entities=merged_entities,
        )
