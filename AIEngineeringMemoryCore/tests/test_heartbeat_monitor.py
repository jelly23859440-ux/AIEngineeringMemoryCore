import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from heartbeat_monitor import HeartbeatMonitor


def test_track_message():
    monitor = HeartbeatMonitor(context_limit=1000, heartbeat_ratio=0.8)
    count = monitor.track_message("Hello world, this is a test message.")
    assert count > 0
    assert monitor.total_tokens > 0


def test_threshold_trigger():
    triggered = []

    def callback():
        triggered.append(True)

    monitor = HeartbeatMonitor(context_limit=50, heartbeat_ratio=0.8)
    monitor.register_callback(callback)

    long_text = "Hello world, this is a comprehensive test message with many tokens. " * 20
    monitor.track_message(long_text)
    assert len(triggered) >= 1


def test_reset():
    monitor = HeartbeatMonitor(context_limit=1000)
    monitor.track_message("Some text")
    assert monitor.total_tokens > 0
    monitor.reset()
    assert monitor.total_tokens == 0


def test_force_consolidate():
    triggered = []

    def callback():
        triggered.append(True)

    monitor = HeartbeatMonitor(context_limit=10000)
    monitor.register_callback(callback)
    monitor.force_consolidate()
    assert len(triggered) == 1


def test_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "heartbeat_state.json"
        monitor = HeartbeatMonitor(context_limit=1000, state_path=state_path)
        monitor.track_message("Hello world")
        assert state_path.exists()

        monitor2 = HeartbeatMonitor(context_limit=1000, state_path=state_path)
        assert monitor2.total_tokens > 0


if __name__ == "__main__":
    test_track_message()
    test_threshold_trigger()
    test_reset()
    test_force_consolidate()
    test_persistence()
    print("heartbeat_monitor.py 所有测试通过!")
