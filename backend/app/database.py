from __future__ import annotations

from typing import Any

from .repositories.store import InMemoryStore


store = InMemoryStore()


def get_store() -> InMemoryStore:
    return store


def get_db() -> Any:
    return store
