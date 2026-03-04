import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import get_index_dir, get_storage_dir, ensure_directories


def generate_doc_id() -> str:
    return uuid.uuid4().hex[:8]


def load_file_registry() -> dict:
    registry_path = get_storage_dir() / "file_registry.json"
    if registry_path.exists():
        with open(registry_path) as f:
            return json.load(f)
    return {}


def save_file_registry(registry: dict) -> None:
    registry_path = get_storage_dir() / "file_registry.json"
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)


def load_history() -> list:
    history_path = get_storage_dir() / "history.json"
    if history_path.exists():
        with open(history_path) as f:
            return json.load(f)
    return []


def save_history(history: list) -> None:
    history_path = get_storage_dir() / "history.json"
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)


def add_to_history(query: str, answer: str, doc_ids: list) -> None:
    history = load_history()
    entry = {
        "id": uuid.uuid4().hex[:8],
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "answer": answer,
        "doc_ids": doc_ids,
    }
    history.append(entry)
    save_history(history)


def clear_history() -> None:
    save_history([])


def get_indexed_documents() -> list:
    registry = load_file_registry()
    return list(registry.values())


def get_document_by_id(doc_id: str) -> Optional[dict]:
    registry = load_file_registry()
    return registry.get(doc_id)


def get_document_tree(doc_id: str) -> Optional[dict]:
    doc = get_document_by_id(doc_id)
    if not doc:
        return None
    tree_path = Path(doc["tree_path"])
    if tree_path.exists():
        with open(tree_path) as f:
            return json.load(f)
    return None


def get_all_trees() -> list[dict]:
    trees = []
    registry = load_file_registry()
    for doc_id, doc in registry.items():
        tree_path = Path(doc["tree_path"])
        if tree_path.exists():
            with open(tree_path) as f:
                trees.append({"doc_id": doc_id, "tree": json.load(f), "doc": doc})
    return trees


def register_document(doc_id: str, original_path: str, tree_path: str, title: str) -> None:
    registry = load_file_registry()
    registry[doc_id] = {
        "id": doc_id,
        "original_path": original_path,
        "tree_path": tree_path,
        "title": title,
        "indexed_at": datetime.now().isoformat(),
    }
    save_file_registry(registry)


def unregister_document(doc_id: str) -> bool:
    registry = load_file_registry()
    if doc_id in registry:
        doc = registry[doc_id]
        tree_path = Path(doc["tree_path"])
        if tree_path.exists():
            tree_path.unlink()
        del registry[doc_id]
        save_file_registry(registry)
        return True
    return False
