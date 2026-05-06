import sys
from pathlib import Path

from config import AppConfig, load_config, create_default_config, config_exists
from consolidator import ManagementAIConfig
from memory_hub import AIMemoryHub


def first_time_setup() -> AppConfig:
    print("=" * 50)
    print("  AI记忆中枢 - 首次配置")
    print("=" * 50)
    print()

    api_base = input("API端点 (默认 http://localhost:11434/v1): ").strip()
    if not api_base:
        api_base = "http://localhost:11434/v1"

    api_key = input("API Key (如不需要可留空): ").strip()

    model = input("模型名称 (默认 llama3): ").strip()
    if not model:
        model = "llama3"

    storage_path = input("记忆存储位置 (默认 ./.memory): ").strip()
    if not storage_path:
        storage_path = "./.memory"

    heartbeat_ratio_str = input("心跳固化比例 (默认 0.8): ").strip()
    heartbeat_ratio = float(heartbeat_ratio_str) if heartbeat_ratio_str else 0.8

    create_default_config("config.yaml")

    config = load_config("config.yaml")
    config.management_ai.api_base = api_base
    config.management_ai.api_key = api_key
    config.management_ai.model = model
    config.memory.storage_path = storage_path
    config.memory.heartbeat_ratio = heartbeat_ratio

    from config import save_config
    save_config(config, "config.yaml")

    print()
    print("配置已保存到 config.yaml")
    print()
    return config


def main():
    if not config_exists("config.yaml"):
        print("检测到项目包含 AI记忆中枢。")
        choice = input("是否启动后台记忆管理？[启动/跳过]: ").strip()
        if choice.lower() not in ("启动", "y", "yes", ""):
            print("已跳过。如需启动，请运行 python start.py")
            return
        config = first_time_setup()
    else:
        config = load_config("config.yaml")

    hub = AIMemoryHub(config, root_dir=str(Path.cwd()))
    hub.start()

    print()
    print("AI记忆中枢已后台启动，正在管理本项目记忆。")
    print(f"  模式: {config.memory_manager.mode}")
    print(f"  管理模型: {config.management_ai.model}")
    print(f"  记忆存储: {config.memory.storage_path}")
    print(f"  心跳阈值: {config.memory.heartbeat_ratio * 100:.0f}%")
    print()

    return hub


if __name__ == "__main__":
    main()
