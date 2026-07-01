# 02 — Design Philosophy

**Version:** 1.0.0
**Status:** Stable
**Last Updated:** 2026-07-01
**Depends On:** [01 — Vision](./01-vision.md)

---

## Purpose of This Document

This document defines the design philosophy that guides every architectural decision in Veridia. It explains **why** the architecture makes the choices it makes, not **how** those choices are implemented.

When a new feature, modification, or extension is proposed, the first question should be: "Does this align with the design philosophy?" If the answer is no, the proposal should either be rejected or the philosophy should be explicitly revised — not silently violated.

This document is prescriptive, not descriptive. It sets the standard that the architecture must meet.

---

## The Central Thesis

> **Model truth states, not documents.**

Every other design decision in Veridia follows from this single thesis.

### What This Means

A document is a container of information created at a moment in time. When the world changes, a new document appears. The relationship between the old document and the new document — that one supersedes the other, that a specific fact changed from one value to another, that a specific event triggered the change — is not captured by the documents themselves. It exists in the mind of the reader who compares them.

Traditional retrieval systems store documents. They index their contents. They retrieve chunks by similarity to a query. The fact that Document B supersedes Document A is, at best, metadata. The retrieval layer does not understand it structurally.

Veridia stores **state transitions**, not documents. A document entering the system is analyzed to extract what changed, relative to the current known state. That change — the delta — is stored. The document may then be discarded.

A query does not search for similar documents. It asks: "What was the state of truth at version X?" The system reconstructs that state from the ordered sequence of deltas and returns the relevant facts.

### Why This Matters

When truth is modeled as a sequence of states rather than a collection of documents:

- **Versioning becomes structural.** A version is not a tag on a document. A version is a position in an ordered sequence of state transitions.
- **Causality becomes explicit.** Every state transition records what triggered it. The system knows why a fact changed, not just that it changed.
- **Temporal consistency becomes guaranteed.** A query at version X returns the state at version X. It cannot accidentally include facts from version Y.
- **Auditability becomes inherent.** Every state is reconstructed deterministically from an immutable log. Every response can be traced to the exact deltas that produced it.

---

## Design Principles

These principles operationalize the central thesis. They are ordered by priority. When principles conflict, higher-priority principles take precedence.

---

### Principle 1: Truth Is Temporal

**A fact is not true or false in isolation. A fact is true or false at a specific version.**

There is no such thing as "the current data retention period" without specifying "as of when." Veridia never exposes a fact without its version context. A query that does not specify a version implicitly resolves to the current truth — the highest version tag — but the version is always present in the response.

**Implication:** Every retrieval operation must be scoped to a version tag. The system must never return a fact without knowing which version it belongs to.

**Violation example:** Returning a fact from the latest delta without indicating that it supersedes a prior value would violate this principle.

---

### Principle 2: Causality Is First-Class

**Every change to knowledge has a cause. That cause must be recorded and retrievable.**

When a fact changes, the system records not just the old and new values, but the causal trigger: the event, document, decision, or correction that produced the change. This enables queries that ask not just "what is true?" but "why is this true?" and "what was true before?"

**Implication:** The delta schema must include a causal trigger field. This field is not optional metadata — it is a required structural element.

**Violation example:** A delta that records a value change without recording what caused the change would violate this principle.

---

### Principle 3: State Reconstruction Is Deterministic

**Given the same initial state and the same ordered sequence of deltas, the system must always produce the same truth state.**

There is no randomness, no ranking, no probabilistic retrieval, and no non-deterministic computation in state reconstruction. This property enables:

- **Auditability:** Any state can be independently verified by replaying the delta log
- **Reproducibility:** The same query always produces the same response
- **Trust:** The system's output is not influenced by model drift, embedding staleness, or ranking heuristics

**Implication:** The state reconstruction algorithm must be purely functional. It must not depend on external state, random seeds, model outputs, or system time.

**Violation example:** Using an LLM to "merge" deltas at reconstruction time would violate this principle. The LLM may be used at query time for synthesis, but not for state reconstruction.

---

### Principle 4: Deltas Are Immutable

**Once a delta is stored, it is never modified, deleted, or reordered.**

Corrections to knowledge arrive as new deltas that supersede prior ones. The original delta remains in the log. This preserves the full history of knowledge evolution and enables reconstruction of any historical state, including states that were later found to be incorrect.

**Implication:** The storage layer must be append-only. There is no update or delete operation on deltas. Version tags are immutable once assigned.

**Violation example:** Modifying a delta's value because a correction was issued would violate this principle. The correction must be a new delta.

---

### Principle 5: Knowledge Atoms Have Persistent Identity

**A fact that changes is the same fact, not a new fact.**

If the data retention period changes from 90 days to 30 days, the atom "data_retention_period" is the same entity before and after the change. The delta modifies its value; it does not create a new atom. This identity persistence is what enables trajectory tracking — the ordered sequence of changes to the same atom over time.

**Implication:** The system must have a mechanism to assign and maintain stable atom identifiers. Two deltas that modify the same atom must reference the same identifier.

**Violation example:** Assigning a new identifier to "data_retention_period" every time it changes would violate this principle and make trajectory queries impossible.

---

### Principle 6: Documents Are Ephemeral

**The document is not the knowledge. The document is evidence of a change in knowledge.**

Once a document has been transformed into deltas, the original document is no longer needed by the system. It may be archived for reference, but it is not part of the retrieval path. Queries resolve against reconstructed states, not against stored documents.

**Implication:** The transformation stage is the critical path. The quality of delta extraction determines the quality of the entire system. The document storage strategy is an operational concern, not an architectural one.

**Violation example:** Retrieving the original document text and using it as context for the LLM instead of the extracted deltas would violate this principle.

---

### Principle 7: Retrieval Is by State, Not by Similarity

**The system retrieves facts from a specific version state. It does not search for similar content.**

When a user queries "what is the data retention period?", the system does not search for documents that contain the phrase "data retention period." It identifies the relevant knowledge atom, determines the target version, and returns the atom's value at that version.

This is a lookup operation, not a search operation.

**Implication:** The retrieval mechanism requires that queries can be mapped to atoms and version tags. The LLM performs this mapping at query interpretation time. Once mapped, retrieval is deterministic.

**Violation example:** Using cosine similarity between the query embedding and delta embeddings to rank results would violate this principle.

---

### Principle 8: The LLM Is the Cognitive Layer, Not the Memory

**Veridia manages knowledge. The LLM interprets, navigates, and synthesizes.**

The boundary is explicit:

- **Veridia (Memory Layer):** Stores deltas, reconstructs states, resolves trajectories, provides structured retrieval results
- **LLM (Cognitive Layer):** Interprets natural language queries, maps them to atoms and version tags, navigates between states, synthesizes natural language responses

The LLM does not store knowledge. Veridia does not understand natural language. The interface between them is structured data.

**Implication:** The output of every retrieval operation must be a structured, typed result that an LLM can consume without parsing natural language. The LLM's prompts are not part of the architecture — they are an implementation detail of the cognitive layer.

**Violation example:** Storing knowledge in the LLM's context window or fine-tuned weights as the primary source of truth would violate this principle.

---

## Tradeoffs

Every design principle implies a tradeoff. These tradeoffs are accepted as inherent to the architecture.

### Tradeoff 1: Ingestion Cost vs. Retrieval Determinism

**Cost:** Transforming documents into deltas requires more computation at ingestion time than chunking and embedding.
**Benefit:** Retrieval is deterministic, temporally consistent, and auditable.
**Decision:** Accept higher ingestion cost in exchange for retrieval guarantees.

### Tradeoff 2: Query Flexibility vs. Temporal Consistency

**Cost:** Veridia does not support open-ended semantic search. Queries must resolve against known atoms.
**Benefit:** Every query result is temporally consistent. No response combines facts from different versions.
**Decision:** Accept constrained query flexibility in exchange for temporal consistency guarantees.

### Tradeoff 3: Structured Knowledge vs. Unstructured Text

**Cost:** Veridia requires that knowledge can be expressed as identifiable atoms. Unstructured text without clear factual boundaries is not supported.
**Benefit:** Atoms enable identity persistence, trajectory tracking, and deterministic retrieval.
**Decision:** Accept the atom requirement as a scope constraint. Veridia is not a general-purpose retrieval system.

### Tradeoff 4: Append-Only Storage vs. Mutability

**Cost:** Corrections create new deltas rather than modifying existing ones. Storage grows monotonically.
**Benefit:** Full history is preserved. Any state can be reconstructed. Audit trail is complete.
**Decision:** Accept monotonic storage growth in exchange for immutability and auditability.

---

## What the Design Philosophy Explicitly Rejects

To prevent architectural drift, the following approaches are explicitly rejected:

- **Embedding-based retrieval.** Veridia does not use vector similarity for retrieval. The architecture is designed to operate without embeddings.
- **Document-grounded responses.** The LLM synthesizes responses from structured state data, not from retrieved document chunks.
- **Probabilistic state reconstruction.** There is no "approximate" or "likely" state. State reconstruction is exact and deterministic.
- **Heuristic version resolution.** Version precedence is determined by explicit ordering, not by recency heuristics or confidence scores.
- **Inline knowledge updates.** Deltas are never modified in place. All changes are append-only.

---

## Relationship to Other Documents

| Document | Relationship |
|---|---|
| [01 — Vision](./01-vision.md) | Defines what Veridia is for; this document defines how we think about building it |
| [03 — Core Concepts](./03-core-concepts.md) | Formalizes the concepts introduced here (delta, truth state, atom, etc.) |
| [04 — Delta Schema](./04-delta-schema.md) | Derives the delta structure from Principles 2, 4, and 5 |
| [05 — State Model](./05-state-model.md) | Derives state reconstruction from Principles 1 and 3 |
| [06 — Retrieval Model](./06-retrieval-model.md) | Derives retrieval semantics from Principles 7 and 8 |
| [ADRs](./adrs/) | Records specific decisions that apply these principles |

---

## Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-07-01 | Initial release |