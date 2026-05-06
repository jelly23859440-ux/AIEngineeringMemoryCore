import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from consolidator import Consolidator, ManagementAIConfig


def test_config_model():
    config = ManagementAIConfig(
        api_base="http://localhost:11434/v1",
        model="llama3",
    )
    assert config.model == "llama3"
    assert config.max_retries == 3
    assert config.timeout == 60


def test_fallback_to_plain_summary():
    config = ManagementAIConfig()
    consolidator = Consolidator(config)
    packet = consolidator._fallback_to_plain_summary("This is a test summary of the conversation.")
    assert len(packet.episodes) == 1
    assert packet.episodes[0].summary_text == "This is a test summary of the conversation."
    assert packet.episodes[0].confidence == "medium"


def test_parse_valid_json():
    config = ManagementAIConfig()
    consolidator = Consolidator(config)

    json_response = '''{
        "episodes": [
            {
                "summary_text": "讨论了支付网关选择",
                "confidence": "high",
                "related_entity_names": ["payment_gateway"]
            }
        ],
        "entities": [
            {
                "entity_name": "payment_gateway",
                "entity_type": "decision",
                "exact_value": "stripe",
                "confidence": "high"
            }
        ]
    }'''

    packet = consolidator._parse_response(json_response)
    assert len(packet.episodes) == 1
    assert packet.episodes[0].summary_text == "讨论了支付网关选择"
    assert len(packet.entities) == 1
    assert packet.entities[0].entity_name == "payment_gateway"


def test_parse_code_block_json():
    config = ManagementAIConfig()
    consolidator = Consolidator(config)

    response = '''```json
    {
        "episodes": [
            {
                "summary_text": "代码块内JSON测试",
                "confidence": "medium",
                "related_entity_names": []
            }
        ],
        "entities": []
    }
    ```'''

    packet = consolidator._parse_response(response)
    assert packet.episodes[0].summary_text == "代码块内JSON测试"


def test_extract_json():
    config = ManagementAIConfig()
    consolidator = Consolidator(config)

    text = 'Some text before {"key": "value"} and after'
    result = consolidator._extract_json(text)
    assert '"key": "value"' in result


def test_normalize_confidence():
    config = ManagementAIConfig()
    consolidator = Consolidator(config)

    assert consolidator._normalize_confidence("HIGH") == "high"
    assert consolidator._normalize_confidence("unknown") == "medium"


if __name__ == "__main__":
    test_config_model()
    test_fallback_to_plain_summary()
    test_parse_valid_json()
    test_parse_code_block_json()
    test_extract_json()
    test_normalize_confidence()
    print("consolidator.py 所有测试通过!")
