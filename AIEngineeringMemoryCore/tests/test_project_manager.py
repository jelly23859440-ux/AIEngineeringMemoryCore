import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from project_manager import ProjectManager


def test_initialize():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = ProjectManager(tmpdir)
        pm.initialize()

        assert pm.summaries_dir.exists()
        assert pm.entities_dir.exists()
        assert pm.cold_dir.exists()
        assert pm.backup_dir.exists()
        assert pm.is_initialized()


def test_memory_isolation():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm1 = ProjectManager(str(Path(tmpdir) / "proj_a"))
        pm2 = ProjectManager(str(Path(tmpdir) / "proj_b"))
        pm1.initialize()
        pm2.initialize()

        assert pm1.memory_dir != pm2.memory_dir
        assert pm1.memory_dir.exists()
        assert pm2.memory_dir.exists()


def test_list_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = ProjectManager(tmpdir)
        pm.initialize()
        assert pm.list_summaries() == []
        assert pm.list_entities() == []
        assert pm.list_cold() == []


def test_clear_all():
    with tempfile.TemporaryDirectory() as tmpdir:
        pm = ProjectManager(tmpdir)
        pm.initialize()
        assert pm.memory_dir.exists()
        pm.clear_all_memory()
        assert not pm.memory_dir.exists()


if __name__ == "__main__":
    test_initialize()
    test_memory_isolation()
    test_list_empty()
    test_clear_all()
    print("project_manager.py 所有测试通过!")
