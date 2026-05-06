import json
from pathlib import Path
from typing import Optional, List, Dict

from project_manager import ProjectManager
from models import MemoryPacket, EpisodeSummary, EntityRecord, file_to_packet, packet_to_file


class ColdStorageManager:
    def __init__(self, project_manager: ProjectManager, enabled: bool = True):
        self.project_manager = project_manager
        self.enabled = enabled

    @property
    def cold_index_path(self) -> Path:
        return self.project_manager.cold_index_path

    def _load_cold_index(self) -> dict:
        if not self.cold_index_path.exists():
            return {}
        try:
            return json.loads(self.cold_index_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_cold_index(self, index: dict) -> None:
        self.cold_index_path.parent.mkdir(parents=True, exist_ok=True)
        self.cold_index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    def mark_subtask_complete(self, task_id: str, keywords: List[str]) -> None:
        if not self.enabled:
            return

        packet_file = self.project_manager.get_cold_path(task_id)

        all_summaries = []
        all_entities = []
        for summary_path in self.project_manager.list_summaries():
            try:
                ep = EpisodeSummary.model_validate_json(summary_path.read_text(encoding="utf-8"))
                ep.is_cold = True
                ep.trigger_keywords = keywords
                all_summaries.append(ep)
                summary_path.unlink()
            except Exception:
                continue

        for entity_path in self.project_manager.list_entities():
            try:
                ent = EntityRecord.model_validate_json(entity_path.read_text(encoding="utf-8"))
                ent.source_episode_id = task_id
                all_entities.append(ent)
                entity_path.unlink()
            except Exception:
                continue

        packet = MemoryPacket(
            episodes=all_summaries,
            entities=all_entities,
            source_task_id=task_id,
        )
        packet_to_file(packet, packet_file)

        cold_index = self._load_cold_index()
        cold_index[task_id] = {
            "keywords": keywords,
            "packet_path": str(packet_file),
            "episode_count": len(all_summaries),
            "entity_count": len(all_entities),
        }
        self._save_cold_index(cold_index)

    def archive_to_cold(self, task_id: str, packet: MemoryPacket) -> None:
        if not self.enabled:
            return

        packet_file = self.project_manager.get_cold_path(task_id)
        packet_to_file(packet, packet_file)

        for ep in packet.episodes:
            ep.is_cold = True

        cold_index = self._load_cold_index()
        cold_index[task_id] = {
            "keywords": list({kw for ep in packet.episodes for kw in ep.trigger_keywords}),
            "packet_path": str(packet_file),
            "episode_count": len(packet.episodes),
            "entity_count": len(packet.entities),
        }
        self._save_cold_index(cold_index)

    def check_keywords_triggered(self, query: str) -> List[str]:
        if not self.enabled:
            return []

        query_lower = query.lower()
        cold_index = self._load_cold_index()
        triggered_tasks: List[str] = []

        for task_id, info in cold_index.items():
            keywords = info.get("keywords", [])
            for kw in keywords:
                if kw.lower() in query_lower:
                    triggered_tasks.append(task_id)
                    break

        return triggered_tasks

    def activate_cold_memory(self, task_id: str) -> Optional[MemoryPacket]:
        if not self.enabled:
            return None

        packet_file = self.project_manager.get_cold_path(task_id)
        if not packet_file.exists():
            return None

        try:
            return file_to_packet(packet_file)
        except Exception:
            return None

    def get_all_cold_keywords(self) -> Dict[str, List[str]]:
        if not self.enabled:
            return {}

        cold_index = self._load_cold_index()
        return {tid: info.get("keywords", []) for tid, info in cold_index.items()}

    def list_cold_task_ids(self) -> List[str]:
        cold_index = self._load_cold_index()
        return list(cold_index.keys())
