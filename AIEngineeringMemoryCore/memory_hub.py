from pathlib import Path
from typing import Optional, List

from config import AppConfig, ManagementAIConfigModel
from project_manager import ProjectManager
from heartbeat_monitor import HeartbeatMonitor
from consolidator import Consolidator, ManagementAIConfig
from cold_storage_manager import ColdStorageManager
from memory_retriever import MemoryRetriever
from memory_manager_scheduler import MemoryManagerScheduler
from memory_consolidation_processor import MemoryConsolidationProcessor
from models import MemoryPacket


MEMORY_COLLABORATION_PROTOCOL = """[记忆协作协议 - AI记忆中枢]
请遵循以下记忆使用规则：
1. 优先采用标记为 [可信度: high] 的记忆
2. 对 [可信度: medium] 的记忆可参考但自行判断
3. 对 [可信度: low] 或 [manual_corrected] 的记忆谨慎参考
4. 若发现记忆与事实矛盾，明确指出并建议用户更新
5. 需要精确值时，直接引用并说明来源"""


class AIMemoryHub:
    def __init__(self, config: AppConfig, root_dir: Optional[str] = None):
        self.config = config
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()

        self.project_manager = ProjectManager(str(self.root_dir))
        self.project_manager.initialize()

        mgmt_config = ManagementAIConfig(
            api_base=config.management_ai.api_base,
            api_key=config.management_ai.api_key,
            model=config.management_ai.model,
            max_retries=config.management_ai.max_retries,
            timeout=config.management_ai.timeout,
            temperature=config.management_ai.temperature,
        )

        self.consolidator = Consolidator(mgmt_config)

        self.cold_manager = ColdStorageManager(
            self.project_manager,
            enabled=config.memory.cold_storage_enabled,
        )

        self.retriever = MemoryRetriever(
            self.project_manager,
            embed_model=config.retrieval.embed_model,
            embed_api_base=config.retrieval.embed_api_base,
            top_k=config.retrieval.top_k_summaries,
            top_m=config.retrieval.top_m_entities,
        )
        self.retriever.initialize_chroma()

        self.heartbeat = HeartbeatMonitor(
            context_limit=config.memory.context_limit,
            heartbeat_ratio=config.memory.heartbeat_ratio,
            state_path=self.project_manager.heartbeat_state_path,
        )

        self.scheduler = MemoryManagerScheduler(
            mode=config.memory_manager.mode,
            async_heartbeat_batch=config.memory_manager.async_heartbeat_batch,
            consolidator=self.consolidator,
            retriever=self.retriever,
            cold_manager=self.cold_manager,
        )

        self.processor = MemoryConsolidationProcessor(
            self.consolidator, self.project_manager
        )

        self.heartbeat.register_callback(self._on_heartbeat_consolidation)

    def start(self) -> None:
        self.scheduler.start()

    def stop(self) -> None:
        self.scheduler.stop()
        self.consolidator.close()
        self.retriever.close()

    def record_exchange(self, user_msg: str, ai_response: str) -> None:
        self.heartbeat.track_message(user_msg)
        self.heartbeat.track_message(ai_response)
        self.scheduler.record_exchange(user_msg, ai_response)

    def retrieve_relevant_memories(self, query: str) -> str:
        episodes, entities = self.retriever.retrieve(query, self.cold_manager)
        return self.retriever._format_context(episodes, entities)

    def inject_memory_context(self, query: str) -> str:
        memory_context = self.retrieve_relevant_memories(query)
        if not memory_context or memory_context.strip() == "[系统记忆回溯 - AI记忆中枢]":
            return ""
        return memory_context

    def mark_subtask_complete(self, task_id: str, keywords: List[str]) -> None:
        self.cold_manager.mark_subtask_complete(task_id, keywords)

    def get_memory_protocol(self) -> str:
        return MEMORY_COLLABORATION_PROTOCOL

    def get_pending_packets(self) -> List[MemoryPacket]:
        return self.scheduler.get_consolidated_packets()

    def consolidate_pending(self) -> Optional[MemoryPacket]:
        packets = self.scheduler.get_consolidated_packets()
        if not packets:
            return None
        return self.processor.process(packets)

    def _on_heartbeat_consolidation(self) -> None:
        self.scheduler.emergency_consolidate()
        self.heartbeat.set_consolidation_complete()
        self.heartbeat.reset()
