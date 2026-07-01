# Veridia MVP

The Veridia MVP is a minimal implementation of the core architectural concepts described in the project documentation.

Its purpose is to demonstrate that the fundamental ideas behind Veridia can be implemented in a simple, deterministic, and reproducible system.

The MVP prioritizes architectural correctness over performance, scalability, or production readiness.

---

# Goals

The MVP demonstrates the following capabilities:

- Ingest structured documents.
- Transform documents into versioned deltas.
- Store deltas in an append-only log.
- Reconstruct historical truth states deterministically.
- Retrieve the current truth state.
- Retrieve historical truth states.
- Retrieve the trajectory of changes for a knowledge atom.

The MVP intentionally excludes advanced optimizations and production infrastructure.

---

# Scope

The MVP focuses only on validating the architectural model.

Implemented features include:

- Delta generation.
- Version tags.
- Knowledge atoms.
- Truth state reconstruction.
- Trajectory reconstruction.
- Basic query execution.
- JSON-based storage.

Not included:

- Distributed storage.
- Concurrency.
- Conflict resolution.
- Authentication.
- Authorization.
- Network services.
- Database backends.
- Performance optimizations.
- Production APIs.

---

# Directory Structure

```text
mvp/
├── README.md
├── main.py
├── models.py
├── storage.py
├── retrieval.py
├── requirements.txt
├── sample_data/
└── tests/
```

---

# Architecture

The MVP follows the same high-level pipeline described in the project documentation.

```
Document
    │
    ▼
Transformation
    │
    ▼
Delta Generation
    │
    ▼
Append-Only Storage
    │
    ▼
State Reconstruction
    │
    ▼
Query Execution
    │
    ▼
Response
```

---

# Example Workflow

1. A document is ingested.
2. The document is transformed into one or more deltas.
3. Deltas are stored in chronological order.
4. A query specifies a target version.
5. The system reconstructs the corresponding truth state.
6. The requested information is returned.

---

# Design Principles

The MVP preserves the architectural principles of Veridia:

- Deterministic reconstruction.
- Immutable delta storage.
- Explicit versioning.
- Causal traceability.
- Separation between semantic and episodic retrieval.

---

# Running the MVP

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the example:

```bash
python main.py
```

---

# Expected Output

A typical execution demonstrates:

- Document ingestion.
- Delta generation.
- Stored delta log.
- Current truth state.
- Historical truth state.
- Trajectory reconstruction.

The exact output depends on the sample dataset provided.

---

# Limitations

This MVP is intended only as a proof of concept.

It should not be considered production-ready software.

Known limitations include:

- Single-process execution.
- In-memory or file-based storage.
- Simplified document transformation.
- Limited error handling.
- No scalability optimizations.

These limitations are intentional and allow the implementation to remain focused on validating the architectural model.

---

# Relationship to the Architecture

The MVP is an implementation of the concepts described in:

- `README.md`
- `architecture/`
- `examples/`

Where implementation choices differ from the architecture documentation, the documentation should be considered the authoritative reference.

---

# Future Work

Future versions may include:

- Persistent database backends.
- Concurrent ingestion.
- Conflict resolution strategies.
- Distributed execution.
- LLM integration.
- REST and gRPC APIs.
- Performance optimizations.
- Benchmark integration.

These features are outside the scope of the MVP but align with the long-term roadmap of the project.