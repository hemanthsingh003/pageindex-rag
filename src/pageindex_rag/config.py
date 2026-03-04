import os
import json
from pathlib import Path
from platformdirs import user_config_dir


def get_config_dir() -> Path:
    return Path(user_config_dir("pageindex-rag"))


def get_index_dir() -> Path:
    return get_config_dir() / "index"


def get_storage_dir() -> Path:
    return get_config_dir()


def ensure_directories() -> None:
    config_dir = get_config_dir()
    index_dir = get_index_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)


def get_default_model() -> str:
    return "mlx-community/Llama-3.2-3B-Instruct-4bit"


def load_config() -> dict:
    config_path = get_config_dir() / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {
        "model": get_default_model(),
    }


def save_config(config: dict) -> None:
    config_path = get_config_dir() / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def get_model() -> str:
    config = load_config()
    return config.get("model", get_default_model())
