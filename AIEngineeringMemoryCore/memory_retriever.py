import json
from typing import Optional, List, Tuple

import chromadb
import httpx
from chromadb.config import Settings as ChromaSettings

from project_manager import ProjectManager
from cold_storage_manager import ColdStorageManager
from models import MemoryPacket, EpisodeSummary, EntityRecord, file_to_packet


EMBED_API_SUFFIX = "/api/embeddings"


class MemoryRetriever:
    SUMMARIES_COLLECTION = "summaries"
    ENTITIES_COLLECTION = "entities"

    def __init__(
        self,
        project_manager: ProjectManager,
        embed_model: str = "nomic-embed-text",
        embed_api_base: str = "http://localhost:11434",
        top_k: int = 5,
        top_m: int = 10,
    ):
        self.project_manager = project_manager
        self.embed_model = embed_model
        self.embed_api_base = embed_api_base.rstrip("/")
        self.top_k = top_k
        self.top_m = top_m

        self._chroma_client: Optional[chromadb.PersistentClient] = None
        self._summaries_collection: Optional[chromadb.Collection] = None
        self._entities_collection: Optional[chromadb.Collection] = None
        self._http_client: Optional[httpx.Client] = None

    @property
    def chroma_client(self) -> chromadb.PersistentClient:
        if self._chroma_client is None:
            chroma_path = str(self.project_manager.memory_dir / "chroma")
            self._chroma_client = chromadb.PersistentClient(
                path=chroma_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._chroma_client

    @property
    def http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=30)
        return self._http_client

    def initialize_chroma(self) -> None:
        try:
            self._summaries_collection = self.chroma_client.get_or_create_collection(
                name=self.SUMMARIES_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:
            self.chroma_client.delete_collection(self.SUMMARIES_COLLECTION)
            self._summaries_collection = self.chroma_client.create_collection(
                name=self.SUMMARIES_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )

        try:
            self._entities_collection = self.chroma_client.get_or_create_collection(
                name=self.ENTITIES_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:
            self.chroma_client.delete_collection(self.ENTITIES_COLLECTION)
            self._entities_collection = self.chroma_client.create_collection(
                name=self.ENTITIES_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )

    @property
    def summaries_collection(self) -> chromadb.Collection:
        if self._summaries_collection is None:
            self.initialize_chroma()
        return self._summaries_collection  # type: ignore[return-value]

    @property
    def entities_collection(self) -> chromadb.Collection:
        if self._entities_collection is None:
            self.initialize_chroma()
        return self._entities_collection  # type: ignore[return-value]

    def retrieve(
        self, query: str, cold_storage_manager: ColdStorageManager
    ) -> Tuple[List[EpisodeSummary], List[EntityRecord]]:
        triggered_tasks = cold_storage_manager.check_keywords_triggered(query)

        cold_episodes: List[EpisodeSummary] = []
        cold_entities: List[EntityRecord] = []
        for task_id in triggered_tasks:
            packet = cold_storage_manager.activate_cold_memory(task_id)
            if packet:
                cold_episodes.extend(packet.episodes)
                cold_entities.extend(packet.entities)

        query_embedding = self._get_embedding(query)

        try:
            summary_results = self.summaries_collection.query(
                query_embeddings=[query_embedding],
                n_results=self.top_k,
            )
        except Exception:
            summary_results = {"ids": [[]], "metadatas": [[]], "distances": [[]]}

        try:
            entity_results = self.entities_collection.query(
                query_embeddings=[query_embedding],
                n_results=self.top_m,
            )
        except Exception:
            entity_results = {"ids": [[]], "metadatas": [[]], "distances": [[]]}

        hot_episodes: List[EpisodeSummary] = []
        for ep_id in summary_results.get("ids", [[]])[0]:
            ep_path = self.project_manager.get_summary_path(ep_id)
            if ep_path.exists():
                try:
                    hot_episodes.append(
                        EpisodeSummary.model_validate_json(ep_path.read_text(encoding="utf-8"))
                    )
                except Exception:
                    continue

        hot_entities: List[EntityRecord] = []
        for ent_id in entity_results.get("ids", [[]])[0]:
            ent_path = self.project_manager.get_entity_path(ent_id)
            if ent_path.exists():
                try:
                    hot_entities.append(
                        EntityRecord.model_validate_json(ent_path.read_text(encoding="utf-8"))
                    )
                except Exception:
                    continue

        all_episodes = hot_episodes + cold_episodes
        all_entities = hot_entities + cold_entities

        seen_entity_names = set()
        deduped_entities: List[EntityRecord] = []
        for ent in all_entities:
            key = (ent.entity_name, ent.entity_type)
            if key not in seen_entity_names:
                seen_entity_names.add(key)
                deduped_entities.append(ent)

        return all_episodes[:self.top_k], deduped_entities[:self.top_m]

    def index_episode(self, episode: EpisodeSummary) -> None:
        embedding = self._get_embedding(episode.summary_text)
        meta = {
            "confidence": episode.confidence,
            "is_cold": str(episode.is_cold),
            "created_at": episode.created_at.isoformat(),
        }

        episode_path = self.project_manager.get_summary_path(episode.episode_id)
        from models import packet_to_json
        episode_path.parent.mkdir(parents=True, exist_ok=True)
        episode_path.write_text(
            episode.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        existing = self.summaries_collection.get(ids=[episode.episode_id])
        if existing and existing["ids"]:
            self.summaries_collection.update(
                ids=[episode.episode_id],
                embeddings=[embedding],
                metadatas=[meta],
            )
        else:
            self.summaries_collection.add(
                ids=[episode.episode_id],
                embeddings=[embedding],
                metadatas=[meta],
                documents=[episode.summary_text],
            )

    def index_entity(self, entity: EntityRecord) -> None:
        embedding = self._get_embedding(f"{entity.entity_name}: {entity.exact_value}")
        meta = {
            "entity_name": entity.entity_name,
            "entity_type": entity.entity_type,
            "confidence": entity.confidence,
        }

        entity_path = self.project_manager.get_entity_path(entity.entity_id)
        entity_path.parent.mkdir(parents=True, exist_ok=True)
        entity_path.write_text(
            entity.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        existing = self.entities_collection.get(ids=[entity.entity_id])
        if existing and existing["ids"]:
            self.entities_collection.update(
                ids=[entity.entity_id],
                embeddings=[embedding],
                metadatas=[meta],
            )
        else:
            self.entities_collection.add(
                ids=[entity.entity_id],
                embeddings=[embedding],
                metadatas=[meta],
                documents=[f"{entity.entity_name}: {entity.exact_value}"],
            )

    def index_packet(self, packet: MemoryPacket) -> None:
        for episode in packet.episodes:
            self.index_episode(episode)
        for entity in packet.entities:
            self.index_entity(entity)

    def remove_episode(self, episode_id: str) -> None:
        try:
            self.summaries_collection.delete(ids=[episode_id])
        except Exception:
            pass
        ep_path = self.project_manager.get_summary_path(episode_id)
        if ep_path.exists():
            ep_path.unlink()

    def remove_entity(self, entity_id: str) -> None:
        try:
            self.entities_collection.delete(ids=[entity_id])
        except Exception:
            pass
        ent_path = self.project_manager.get_entity_path(entity_id)
        if ent_path.exists():
            ent_path.unlink()

    def _get_embedding(self, text: str) -> List[float]:
        url = f"{self.embed_api_base}{EMBED_API_SUFFIX}"
        response = self.http_client.post(
            url,
            json={"model": self.embed_model, "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]

    def _format_context(
        self,
        episodes: List[EpisodeSummary],
        entities: List[EntityRecord],
    ) -> str:
        lines = ["[系统记忆回溯 - AI记忆中枢]"]

        if episodes:
            lines.append("")
            for ep in episodes:
                lines.append(f"- {ep.summary_text} [可信度: {ep.confidence}]")

        if entities:
            lines.append("")
            lines.append("相关精确实体：")
            for ent in entities:
                value_str = str(ent.exact_value)
                lines.append(
                    f"- {ent.entity_name} = {value_str} [可信度: {ent.confidence}]"
                )

        return "\n".join(lines)

    def close(self) -> None:
        if self._http_client:
            self._http_client.close()
            self._http_client = None
        self._summaries_collection = None
        self._entities_collection = None
        if self._chroma_client:
            try:
                self._chroma_client._system.stop()
            except Exception:
                pass
            self._chroma_client = None
