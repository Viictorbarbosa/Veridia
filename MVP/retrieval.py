"""
Veridia MVP

Deterministic state reconstruction and retrieval.
"""

from typing import Optional

from models import Delta, Trajectory, TruthState, VersionTag
from storage import DeltaStore


class StateReconstructor:
    """
    Reconstructs truth states from an append-only delta log.
    """

    def __init__(self, store: DeltaStore):
        self.store = store

    def reconstruct(self, version: VersionTag) -> TruthState:
        """
        Reconstruct the truth state at the specified version.
        """
        state = TruthState(version=version)

        deltas = self.store.up_to_version(version)

        for delta in deltas:
            if delta.operation in ("set", "add", "update"):
                state.atoms[delta.atom_id] = delta.value

            elif delta.operation == "remove":
                state.atoms.pop(delta.atom_id, None)

        return state

    def current_state(self) -> Optional[TruthState]:
        """
        Return the latest truth state.
        """
        latest = self.store.latest_version()

        if latest is None:
            return None

        return self.reconstruct(latest)


class TrajectoryResolver:
    """
    Retrieves the complete change history of a knowledge atom.
    """

    def __init__(self, store: DeltaStore):
        self.store = store

    def resolve(self, atom_id: str) -> Trajectory:
        """
        Return the ordered trajectory for a knowledge atom.
        """
        deltas = self.store.by_atom(atom_id)

        deltas.sort(key=lambda d: d.version.value)

        return Trajectory(
            atom_id=atom_id,
            deltas=deltas
        )


class QueryEngine:
    """
    High-level interface for executing MVP retrieval operations.
    """

    def __init__(self, store: DeltaStore):
        self.store = store
        self.state_reconstructor = StateReconstructor(store)
        self.trajectory_resolver = TrajectoryResolver(store)

    def current_truth(self) -> Optional[TruthState]:
        """
        Retrieve the current truth state.
        """
        return self.state_reconstructor.current_state()

    def truth_at(self, version: VersionTag) -> TruthState:
        """
        Retrieve the truth state at a specific version.
        """
        return self.state_reconstructor.reconstruct(version)

    def trajectory(self, atom_id: str) -> Trajectory:
        """
        Retrieve the trajectory of a knowledge atom.
        """
        return self.trajectory_resolver.resolve(atom_id)