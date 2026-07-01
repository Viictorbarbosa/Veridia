"""
Veridia MVP

Core data models for the Veridia architecture.

These models define the fundamental abstractions used throughout the MVP.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class VersionTag:
    """
    Represents an ordered version identifier.
    """

    value: str


@dataclass(frozen=True)
class KnowledgeAtom:
    """
    Represents the persistent identity of a piece of knowledge.
    """

    atom_id: str
    name: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Delta:
    """
    Represents a single change applied to a knowledge atom.
    """

    delta_id: str
    atom_id: str
    version: VersionTag

    operation: str
    value: Any
    previous_value: Optional[Any]

    cause: str

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TruthState:
    """
    Represents the reconstructed state of knowledge
    at a specific version.
    """

    version: VersionTag

    atoms: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Trajectory:
    """
    Represents the ordered sequence of deltas
    affecting a knowledge atom.
    """

    atom_id: str

    deltas: List[Delta] = field(default_factory=list)


@dataclass
class Document:
    """
    Represents a source document before transformation.
    """

    document_id: str

    version: VersionTag

    content: Dict[str, Any]

    source: str

    metadata: Dict[str, Any] = field(default_factory=dict)