import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory_manager_scheduler import MemoryManagerScheduler


def test_scheduler_init():
    scheduler = MemoryManagerScheduler(mode="hybrid", async_heartbeat_batch=60)
    assert scheduler.mode == "hybrid"
    assert scheduler.async_heartbeat_batch == 60
    assert len(scheduler._pending_exchanges) == 0


def test_record_exchange():
    scheduler = MemoryManagerScheduler(mode="async", async_heartbeat_batch=5)
    scheduler.record_exchange("Hello", "Hi there")
    assert len(scheduler._pending_exchanges) == 2
    assert scheduler._pending_heartbeat_count == 1


def test_start_stop():
    scheduler = MemoryManagerScheduler(mode="async", async_heartbeat_batch=100)
    scheduler.start()
    assert scheduler._running
    scheduler.stop()
    assert not scheduler._running


if __name__ == "__main__":
    test_scheduler_init()
    test_record_exchange()
    test_start_stop()
    print("memory_manager_scheduler.py 所有测试通过!")
