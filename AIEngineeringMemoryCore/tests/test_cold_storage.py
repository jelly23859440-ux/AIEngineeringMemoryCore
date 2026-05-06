import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from project_manager import ProjectManager
from cold_storage_manager import ColdStorageManager
from models import EpisodeSummary, EntityRecord, MemoryPacket


def test_mark_subtask_complete():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = ProjectManager(tmpdir)
        pm.initialize()

        ep = EpisodeSummary(summary_text="支付模块开发", confidence="high")
        ent = EntityRecord(entity_name="gateway", entity_type="decision", exact_value="stripe")

        from models import packet_to_json
        (pm.summaries_dir / f"{ep.episode_id}.json").write_text(
            ep.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (pm.entities_dir / f"{ent.entity_id}.json").write_text(
            ent.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8"
        )

        csm = ColdStorageManager(pm)
        csm.mark_subtask_complete("payment_task", ["支付", "Stripe"])

        assert pm.list_summaries() == []
        assert pm.list_entities() == []
        assert len(pm.list_cold()) == 1


def test_keywords_triggered():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = ProjectManager(tmpdir)
        pm.initialize()
        csm = ColdStorageManager(pm)

        ep = EpisodeSummary(summary_text="退款模块", confidence="high")
        (pm.summaries_dir / f"{ep.episode_id}.json").write_text(
            ep.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8"
        )
        csm.mark_subtask_complete("refund_task", ["退款", "refund", "回调"])

        triggered = csm.check_keywords_triggered("我们需要处理退款回调的问题")
        assert "refund_task" in triggered

        not_triggered = csm.check_keywords_triggered("讨论用户注册流程")
        assert "refund_task" not in not_triggered


def test_disabled():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = ProjectManager(tmpdir)
        pm.initialize()
        csm = ColdStorageManager(pm, enabled=False)

        csm.mark_subtask_complete("task1", ["test"])
        assert csm.check_keywords_triggered("test") == []
        assert csm.activate_cold_memory("task1") is None


if __name__ == "__main__":
    test_mark_subtask_complete()
    test_keywords_triggered()
    test_disabled()
    print("cold_storage_manager.py 所有测试通过!")
