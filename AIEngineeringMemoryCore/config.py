from pathlib import Path
from typing import Optional, Literal

import yaml
from pydantic import BaseModel, Field


class ManagementAIConfigModel(BaseModel):
    api_base: str = "http://localhost:11434/v1"
    api_key: str = ""
    model: str = "llama3"
    max_retries: int = 3
    timeout: int = 60
    temperature: float = 0.3


class MemoryConfig(BaseModel):
    storage_path: str = "./.memory"
    heartbeat_ratio: float = 0.8
    context_limit: int = 4096
    cold_storage_enabled: bool = True


class RetrievalConfig(BaseModel):
    top_k_summaries: int = 5
    top_m_entities: int = 10
    embed_model: str = "nomic-embed-text"
    embed_api_base: str = "http://localhost:11434"


class MemoryManagerConfig(BaseModel):
    mode: Literal["async", "realtime", "hybrid"] = "hybrid"
    async_heartbeat_batch: int = 60


class AppConfig(BaseModel):
    management_ai: ManagementAIConfigModel = Field(default_factory=ManagementAIConfigModel)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    memory_manager: MemoryManagerConfig = Field(default_factory=MemoryManagerConfig)


DEFAULT_CONFIG_YAML = """management_ai:
  api_base: "http://localhost:11434/v1"
  api_key: ""
  model: "llama3"
  max_retries: 3
  timeout: 60
  temperature: 0.3

memory:
  storage_path: "./.memory"
  heartbeat_ratio: 0.8
  context_limit: 4096
  cold_storage_enabled: true

retrieval:
  top_k_summaries: 5
  top_m_entities: 10
  embed_model: "nomic-embed-text"
  embed_api_base: "http://localhost:11434"

memory_manager:
  mode: "hybrid"
  async_heartbeat_batch: 60
"""


def load_config(path: str = "config.yaml") -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(data)


def create_default_config(path: str = "config.yaml") -> None:
    config_path = Path(path)
    config_path.write_text(DEFAULT_CONFIG_YAML, encoding="utf-8")


def save_config(config: AppConfig, path: str = "config.yaml") -> None:
    config_path = Path(path)
    yaml_str = yaml.dump(
        config.model_dump(),
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    config_path.write_text(yaml_str, encoding="utf-8")


def config_exists(path: str = "config.yaml") -> bool:
    return Path(path).exists()
