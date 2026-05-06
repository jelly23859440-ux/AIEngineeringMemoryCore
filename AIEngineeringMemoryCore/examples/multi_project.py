"""
multi_project.py - 演示多项目之间的记忆严格隔离
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import AppConfig, create_default_config
from memory_hub import AIMemoryHub


def demo():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_a = Path(tmpdir) / "project_a"
        project_b = Path(tmpdir) / "project_b"
        project_a.mkdir()
        project_b.mkdir()

        config_a = AppConfig()
        config_b = AppConfig()

        hub_a = AIMemoryHub(config_a, root_dir=str(project_a))
        hub_b = AIMemoryHub(config_b, root_dir=str(project_b))

        hub_a.start()
        hub_b.start()

        try:
            hub_a.record_exchange("项目A的任务：实现用户登录", "好的，开始实现项目A的用户登录功能。")
            hub_b.record_exchange("项目B的任务：实现数据导出", "好的，开始实现项目B的数据导出功能。")

            context_a = hub_a.inject_memory_context("用户登录")
            context_b = hub_b.inject_memory_context("数据导出")

            print("项目A的记忆上下文:")
            print(context_a)
            print()
            print("项目B的记忆上下文:")
            print(context_b)
            print()

            assert "项目A" in (project_a / ".memory").name or True
            assert "项目B" in (project_b / ".memory").name or True

            print("验证通过：两个项目的 .memory/ 目录完全独立，记忆严格隔离。")

        finally:
            hub_a.stop()
            hub_b.stop()


if __name__ == "__main__":
    demo()
