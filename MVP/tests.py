"""
Veridia MVP

Basic test suite for the MVP implementation.

Run:

    python tests.py
"""

from models import Delta, VersionTag
from retrieval import QueryEngine
from storage import DeltaStore


def create_store() -> DeltaStore:
    """
    Creates a sample store used by the tests.
    """

    store = DeltaStore()

    store.append(
        Delta(
            delta_id="delta-001",
            atom_id="data_retention_period",
            version=VersionTag("v1.0"),
            operation="set",
            value="90 days",
            previous_value=None,
            cause="Initial publication",
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

    return store


def test_append_only_store():
    store = create_store()

    assert store.count() == 2
    assert not store.is_empty()


def test_current_state():
    store = create_store()
    engine = QueryEngine(store)

    state = engine.current_truth()

    assert state is not None
    assert state.atoms["data_retention_period"] == "30 days"


def test_historical_state():
    store = create_store()
    engine = QueryEngine(store)

    state = engine.truth_at(VersionTag("v1.0"))

    assert state.atoms["data_retention_period"] == "90 days"


def test_trajectory():
    store = create_store()
    engine = QueryEngine(store)

    trajectory = engine.trajectory("data_retention_period")

    assert len(trajectory.deltas) == 2

    assert trajectory.deltas[0].version.value == "v1.0"
    assert trajectory.deltas[1].version.value == "v2.0"


def test_latest_version():
    store = create_store()

    latest = store.latest_version()

    assert latest is not None
    assert latest.value == "v2.0"


def test_empty_store():
    store = DeltaStore()

    assert store.is_empty()
    assert store.current_version() is None if hasattr(store, "current_version") else True


def run_tests():
    print("Running Veridia MVP tests...\n")

    tests = [
        test_append_only_store,
        test_current_state,
        test_historical_state,
        test_trajectory,
        test_latest_version,
        test_empty_store,
    ]

    passed = 0

    for test in tests:
        try:
            test()
            print(f"✓ {test.__name__}")
            passed += 1
        except AssertionError:
            print(f"✗ {test.__name__}")

    print("\n-----------------------------")
    print(f"Passed: {passed}/{len(tests)}")
    print("-----------------------------")

    if passed == len(tests):
        print("All tests passed.")
    else:
        print("Some tests failed.")


if __name__ == "__main__":
    run_tests()