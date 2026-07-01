"""
Veridia MVP

Minimal demonstration of the Veridia architecture.

Workflow:
1. Create sample deltas.
2. Store them in the append-only log.
3. Reconstruct the latest truth state.
4. Reconstruct a historical truth state.
5. Retrieve the trajectory of a knowledge atom.
"""

from models import Delta, VersionTag
from retrieval import QueryEngine
from storage import DeltaStore


def main() -> None:
    store = DeltaStore()

    # ------------------------------------------------------------------
    # Sample deltas
    # ------------------------------------------------------------------

    store.append(
        Delta(
            delta_id="delta-001",
            atom_id="data_retention_period",
            version=VersionTag("v1.0"),
            operation="set",
            value="90 days",
            previous_value=None,
            cause="Initial policy publication",
        )
    )

    store.append(
        Delta(
            delta_id="delta-002",
            atom_id="data_retention_period",
            version=VersionTag("v2.0"),
            operation="update",
            value="30 days",
            previous_value="90 days",
            cause="Compliance review",
        )
    )

    store.append(
        Delta(
            delta_id="delta-003",
            atom_id="maximum_login_attempts",
            version=VersionTag("v2.0"),
            operation="set",
            value=5,
            previous_value=None,
            cause="Security policy update",
        )
    )

    engine = QueryEngine(store)

    # ------------------------------------------------------------------
    # Current truth state
    # ------------------------------------------------------------------

    print("=" * 60)
    print("CURRENT TRUTH STATE")
    print("=" * 60)

    current = engine.current_truth()

    if current:
        for atom, value in current.atoms.items():
            print(f"{atom}: {value}")

    # ------------------------------------------------------------------
    # Historical truth state
    # ------------------------------------------------------------------

    print("\n" + "=" * 60)
    print("TRUTH STATE AT v1.0")
    print("=" * 60)

    historical = engine.truth_at(VersionTag("v1.0"))

    for atom, value in historical.atoms.items():
        print(f"{atom}: {value}")

    # ------------------------------------------------------------------
    # Trajectory
    # ------------------------------------------------------------------

    print("\n" + "=" * 60)
    print("TRAJECTORY")
    print("=" * 60)

    trajectory = engine.trajectory("data_retention_period")

    for delta in trajectory.deltas:
        print(
            f"{delta.version.value} | "
            f"{delta.operation.upper()} | "
            f"{delta.value} | "
            f"{delta.cause}"
        )


if __name__ == "__main__":
    main()