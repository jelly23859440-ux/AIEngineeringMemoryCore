from pathlib import Path


class ProjectManager:
    MEMORY_DIR_NAME = ".memory"
    SUMMARIES_DIR = "summaries"
    ENTITIES_DIR = "entities"
    COLD_DIR = "cold"
    BACKUP_DIR = ".backup"
    HEARTBEAT_STATE_FILE = "heartbeat_state.json"
    COLD_INDEX_FILE = "cold_index.json"

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir).resolve()
        self._memory_dir: Path | None = None

    @property
    def memory_dir(self) -> Path:
        if self._memory_dir is None:
            self._memory_dir = self.root_dir / self.MEMORY_DIR_NAME
        return self._memory_dir

    @property
    def summaries_dir(self) -> Path:
        return self.memory_dir / self.SUMMARIES_DIR

    @property
    def entities_dir(self) -> Path:
        return self.memory_dir / self.ENTITIES_DIR

    @property
    def cold_dir(self) -> Path:
        return self.memory_dir / self.COLD_DIR

    @property
    def backup_dir(self) -> Path:
        return self.memory_dir / self.BACKUP_DIR

    @property
    def heartbeat_state_path(self) -> Path:
        return self.memory_dir / self.HEARTBEAT_STATE_FILE

    @property
    def cold_index_path(self) -> Path:
        return self.memory_dir / self.COLD_INDEX_FILE

    def initialize(self) -> None:
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        self.entities_dir.mkdir(parents=True, exist_ok=True)
        self.cold_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def is_initialized(self) -> bool:
        return (
            self.summaries_dir.exists()
            and self.entities_dir.exists()
            and self.cold_dir.exists()
        )

    def get_summary_path(self, episode_id: str) -> Path:
        return self.summaries_dir / f"{episode_id}.json"

    def get_entity_path(self, entity_id: str) -> Path:
        return self.entities_dir / f"{entity_id}.json"

    def get_cold_path(self, task_id: str) -> Path:
        return self.cold_dir / f"{task_id}.json"

    def get_backup_path(self, filename: str) -> Path:
        return self.backup_dir / filename

    def list_summaries(self) -> list[Path]:
        if not self.summaries_dir.exists():
            return []
        return sorted(self.summaries_dir.glob("*.json"))

    def list_entities(self) -> list[Path]:
        if not self.entities_dir.exists():
            return []
        return sorted(self.entities_dir.glob("*.json"))

    def list_cold(self) -> list[Path]:
        if not self.cold_dir.exists():
            return []
        return sorted(self.cold_dir.glob("*.json"))

    def clear_all_memory(self) -> None:
        import shutil
        if self.memory_dir.exists():
            shutil.rmtree(self.memory_dir)
