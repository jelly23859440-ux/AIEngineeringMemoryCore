import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from consolidator import Consolidator, ManagementAIConfig
from project_manager import ProjectManager
from memory_consolidation_processor import MemoryConsolidationProcessor
from models import MemoryPacket, EpisodeSummary, EntityRecord


def test_process_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = ProjectManager(tmpdir)
        pm.initialize()
        config = ManagementAIConfig()
        consolidator = Consolidator(config)
        processor = MemoryConsolidationProcessor(consolidator, pm)

        result = processor.process([])
        assert isinstance(result, MemoryPacket)
        assert len(result.episodes) == 0


def test_merge_packets():
    config = ManagementAIConfig()
    consolidator = Consolidator(config)
    pm = ProjectManager("/tmp/test")
    processor = MemoryConsolidationProcessor(consolidator, pm)

    p1 = MemoryPacket(
        episodes=[EpisodeSummary(summary_text="任务A")],
        entities=[EntityRecord(entity_name="key1", entity_type="config", exact_value="v1")],
    )
    p2 = MemoryPacket(
        episodes=[EpisodeSummary(summary_text="任务A")],
        entities=[EntityRecord(entity_name="key1", entity_type="config", exact_value="v1")],
    )
    p3 = MemoryPacket(
        episodes=[EpisodeSummary(summary_text="任务B")],
        entities=[EntityRecord(entity_name="key2", entity_type="config", exact_value="v2")],
    )

    merged = processor.merge_packets([p1, p2, p3])
    assert len(merged.episodes) == 2
    assert len(merged.entities) == 2


def test_backup():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = ProjectManager(tmpdir)
        pm.initialize()
        config = ManagementAIConfig()
        consolidator = Consolidator(config)
        processor = MemoryConsolidationProcessor(consolidator, pm)

        packet = MemoryPacket(episodes=[EpisodeSummary(summary_text="测试")])
        processor._backup_old_entries([packet])

        backups = list(pm.backup_dir.glob("*.json"))
        assert len(backups) == 1


if __name__ == "__main__":
    test_process_empty()
    test_merge_packets()
    test_backup()
    print("memory_consolidation_processor.py 所有测试通过!")
