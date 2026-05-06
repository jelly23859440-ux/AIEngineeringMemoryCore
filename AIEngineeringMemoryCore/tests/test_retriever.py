import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from project_manager import ProjectManager
from cold_storage_manager import ColdStorageManager
from memory_retriever import MemoryRetriever


def test_format_context():
    pm = ProjectManager("/tmp/test_mem")
    retriever = MemoryRetriever(pm)

    from models import EpisodeSummary, EntityRecord
    episodes = [EpisodeSummary(summary_text="完成了用户模块开发", confidence="high")]
    entities = [EntityRecord(entity_name="gateway", entity_type="decision", exact_value="stripe", confidence="high")]

    context = retriever._format_context(episodes, entities)
    assert "系统记忆回溯" in context
    assert "用户模块开发" in context
    assert "gateway" in context
    assert "stripe" in context
    assert "high" in context


if __name__ == "__main__":
    test_format_context()
    print("memory_retriever.py 所有测试通过!")
