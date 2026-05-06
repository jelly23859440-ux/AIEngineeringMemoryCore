"""
custom_config.py - 演示如何使用自定义配置启动AI记忆中枢
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import AppConfig, ManagementAIConfigModel, MemoryConfig, RetrievalConfig, MemoryManagerConfig
from memory_hub import AIMemoryHub


def demo():
    config = AppConfig(
        management_ai=ManagementAIConfigModel(
            api_base="http://localhost:11434/v1",
            api_key="",
            model="llama3",
            max_retries=5,
            timeout=120,
        ),
        memory=MemoryConfig(
            storage_path="./.memory",
            heartbeat_ratio=0.7,
            context_limit=8192,
            cold_storage_enabled=True,
        ),
        retrieval=RetrievalConfig(
            top_k_summaries=8,
            top_m_entities=15,
            embed_model="nomic-embed-text",
            embed_api_base="http://localhost:11434",
        ),
        memory_manager=MemoryManagerConfig(
            mode="hybrid",
            async_heartbeat_batch=40,
        ),
    )

    hub = AIMemoryHub(config, root_dir=str(Path.cwd()))
    hub.start()

    try:
        hub.record_exchange("我们要开发一个数据分析平台。", "好的，让我来设计数据分析平台的架构。")

        result = hub.inject_memory_context("数据分析")
        print("检索结果 (top_k=8, top_m=15):")
        print(result)

        print(f"\n当前心跳token数: {hub.heartbeat.total_tokens}")
        print(f"上下文限制: {hub.heartbeat.context_limit}")
        print(f"心跳阈值比例: {hub.heartbeat.heartbeat_ratio}")
        print(f"调度模式: {config.memory_manager.mode}")
    finally:
        hub.stop()

    print("\n自定义配置演示完成!")


if __name__ == "__main__":
    demo()
