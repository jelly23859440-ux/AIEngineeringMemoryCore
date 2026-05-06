import json
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    EntityRecord,
    EpisodeSummary,
    MemoryPacket,
    HeartbeatState,
    packet_to_json,
    json_to_packet,
    packet_to_file,
    file_to_packet,
    heartbeat_state_to_json,
    json_to_heartbeat_state,
)


def test_entity_record():
    entity = EntityRecord(
        entity_name="payment_gateway",
        entity_type="decision",
        exact_value="stripe",
        confidence="high",
    )
    assert entity.entity_name == "payment_gateway"
    assert entity.confidence == "high"
    assert entity.entity_id

    try:
        EntityRecord(entity_name="", entity_type="test", exact_value="v")
        assert False, "Should have raised ValueError"
    except Exception:
        pass


def test_episode_summary():
    ep = EpisodeSummary(
        summary_text="完成了用户注册模块",
        confidence="high",
        trigger_keywords=["用户", "注册"],
    )
    assert "用户注册" in ep.summary_text
    assert ep.is_cold is False
    assert "用户" in ep.trigger_keywords

    try:
        EpisodeSummary(summary_text="")
        assert False, "Should have raised ValueError"
    except Exception:
        pass


def test_memory_packet():
    ep = EpisodeSummary(summary_text="测试摘要")
    entity = EntityRecord(entity_name="key", entity_type="config", exact_value="val")
    packet = MemoryPacket(episodes=[ep], entities=[entity])
    assert len(packet.episodes) == 1
    assert len(packet.entities) == 1


def test_serialization():
    packet = MemoryPacket(
        episodes=[EpisodeSummary(summary_text="摘要内容")],
        entities=[EntityRecord(entity_name="config_key", entity_type="config", exact_value="secret_value")],
    )

    json_str = packet_to_json(packet)
    assert "摘要内容" in json_str
    assert "config_key" in json_str

    restored = json_to_packet(json_str)
    assert restored.episodes[0].summary_text == "摘要内容"


def test_file_serialization():
    packet = MemoryPacket(
        episodes=[EpisodeSummary(summary_text="文件测试")],
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test_packet.json"
        packet_to_file(packet, filepath)
        assert filepath.exists()
        restored = file_to_packet(filepath)
        assert restored.episodes[0].summary_text == "文件测试"


def test_heartbeat_state():
    state = HeartbeatState(context_limit=4096, heartbeat_ratio=0.8)
    assert state.threshold == 3276
    assert not state.should_consolidate

    state.total_tokens = 4000
    assert state.should_consolidate

    state.is_consolidating = True
    assert not state.should_consolidate


if __name__ == "__main__":
    test_entity_record()
    test_episode_summary()
    test_memory_packet()
    test_serialization()
    test_file_serialization()
    test_heartbeat_state()
    print("models.py 所有测试通过!")
