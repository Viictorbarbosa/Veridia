"""
Veridia MVP

Append-only in-memory storage for deltas.
"""

from typing import Dict, List

from models import Delta, VersionTag


class DeltaStore:
    """
    Simple append-only storage used by the MVP.

    Deltas are never modified or deleted.
    """

    def __init__(self):
        self._deltas: List[Delta] = []

    def append(self, delta: Delta) -> None:
        """
        Store a new delta.
        """
        self._deltas.append(delta)

    def all(self) -> List[Delta]:
        """
        Return all stored deltas.
        """
        return list(self._deltas)

    def by_atom(self, atom_id: str) -> List[Delta]:
        """
        Return all deltas affecting a knowledge atom.
        """
        return [
            delta
            for delta in self._deltas
            if delta.atom_id == atom_id
        ]

    def up_to_version(self, version: VersionTag) -> List[Delta]:
        """
        Return all deltas up to a given version.

        NOTE:
        The MVP assumes that version tags are lexicographically ordered.
        Future versions should replace this with a dedicated version ordering
        strategy.
        """
        return [
            delta
            for delta in self._deltas
            if delta.version.value <= version.value
        ]

    def latest_version(self) -> VersionTag | None:
        """
        Return the latest version currently stored.
        """
        if not self._deltas:
            return None

        return max(
            self._deltas,
            key=lambda d: d.version.value
        ).version

    def count(self) -> int:
        """
        Return the number of stored deltas.
        """
        return len(self._deltas)

    def is_empty(self) -> bool:
        """
        Return True if no deltas are stored.
        """
        return len(self._deltas) == 0

    def clear(self) -> None:
        """
        Clear the storage.

        Intended only for testing.
        """
        self._deltas.clear()