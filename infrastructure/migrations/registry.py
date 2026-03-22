from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class MigrationStep:
    version: str
    apply_fn: Callable[[Any], None]
    description: str = ""


def get_latest_migration_version(steps: Iterable[MigrationStep]) -> str:
    ordered = sorted(steps, key=lambda step: step.version)
    return ordered[-1].version if ordered else ""


def get_pending_migrations(current_version: str, steps: Iterable[MigrationStep]) -> list[MigrationStep]:
    ordered = sorted(steps, key=lambda step: step.version)
    if not current_version:
        return ordered
    return [step for step in ordered if step.version > current_version]
