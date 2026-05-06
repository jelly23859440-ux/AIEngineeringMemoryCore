import gc
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import AppConfig
from memory_hub import AIMemoryHub


def test_hub_init():
    config = AppConfig()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        hub = AIMemoryHub(config, root_dir=tmpdir)
        assert hub.project_manager.is_initialized()
        assert hub.heartbeat is not None
        assert hub.retriever is not None
        assert hub.scheduler is not None
        hub.stop()
        gc.collect()


def test_memory_protocol():
    config = AppConfig()
    hub = AIMemoryHub(config, root_dir="/tmp/test")
    protocol = hub.get_memory_protocol()
    assert "记忆协作协议" in protocol
    assert "可信度: high" in protocol
    assert "可信度: medium" in protocol
    assert "可信度: low" in protocol
    hub.stop()


def test_record_exchange():
    config = AppConfig()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        hub = AIMemoryHub(config, root_dir=tmpdir)
        hub.start()
        hub.record_exchange("用户消息", "AI回复")
        assert hub.heartbeat.total_tokens > 0
        hub.stop()
        gc.collect()


if __name__ == "__main__":
    test_hub_init()
    test_memory_protocol()
    test_record_exchange()
    print("memory_hub.py 所有测试通过!")
