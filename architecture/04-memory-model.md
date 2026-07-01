# Memory Model

**Version:** 1.0.0  
**Status:** Stable  
**Last Updated:** 2026-07-01  
**Depends On:** [01 — Vision](./01-vision.md), [02 — Design Philosophy](./02-design-philosophy.md), [03 — Architectural Principles](./03-architectural-principles.md)

---

## Purpose of This Document

This document defines the conceptual memory model of Veridia. It answers the question: "What exactly is stored inside Veridia, and how is that knowledge organized?"

Previous documents established that Veridia models truth states rather than documents, that versioning is structural rather than cosmetic, and that retrieval operates by state lookup rather than similarity search. This document describes the memory architecture that enables those properties.

This document does not describe implementation details, storage engines, schemas, or algorithms. It describes the logical organization of knowledge within the system — the concepts that every implementation must represent, regardless of the technology used.

---

## The Core Idea

Veridia stores knowledge as a sequence of explicit state transitions. A document entering the system is not stored as a document. It is analyzed to determine what changed relative to the current known state. That change is recorded as a delta. The document may then be discarded. What remains is an ordered, causal, versioned record of how truth evolved.

This model separates two kinds of knowledge that traditional retrieval systems conflate. One is the knowledge of what is true right now — the facts themselves. The other is the knowledge of how those facts came to be true — the history of changes, their causes, and their sequence. Traditional systems store documents and retrieve chunks by similarity. The relationships between versions, the causal triggers of changes, and the temporal validity of facts remain implicit in the documents themselves. Veridia makes them explicit in the memory structure.

The memory model is organized around a single principle: every state of knowledge is the cumulative result of all deltas applied up to a given version. There is no other source of truth. There is no fallback to original documents. The delta log is the complete and sufficient record of everything the system knows.

---

## Memory Layers

Veridia organizes memory into two distinct layers: semantic memory and episodic memory. Each serves a different purpose. Each answers a different kind of question. Both are derived from the same underlying delta log.

### Semantic Memory

Semantic memory holds facts without history. It answers the question: "What is true?" Given a version, semantic memory provides the complete set of atom-value pairs that were simultaneously true at that version. It does not explain how those facts arrived. It does not reference the documents that introduced them. It does not preserve what those facts replaced. It is the net result of all deltas, presented as a coherent snapshot.

When a compliance officer asks "What is the current data retention period?", the answer comes from semantic memory. The system reconstructs the truth state at the latest version, retrieves the value of the relevant atom, and returns it. No history is included because the question did not ask for history.

Semantic memory is the default retrieval mode for queries that do not require provenance. It provides fast access to facts at any version without the overhead of traversing the causal chain.

### Episodic Memory

Episodic memory holds the trajectory of changes. It answers the question: "What happened, when, and why?" Given a knowledge atom and a version range, episodic memory returns the ordered sequence of deltas that affected that atom — each with its cause, its timestamp, and the values it transitioned between.

When an auditor asks "How has the data retention period changed, and what triggered each change?", the answer comes from episodic memory. The system retrieves the trajectory for the relevant atom, presenting each delta in version order with its causal attribution.

Episodic memory preserves the full evolutionary history of knowledge. Nothing is lost. A delta that was later superseded remains in the episodic record. A value that was later found to be incorrect remains traceable. The system can explain not only what is true now, but what was true at any point in the past and why it changed.

### Why Both Layers Exist

Semantic and episodic memory are not alternatives. They are complementary interfaces to the same underlying data. Semantic memory provides efficient access to facts. Episodic memory provides the context that explains those facts. A system with only semantic memory could tell you the current retention period but not why it is 30 days instead of 90. A system with only episodic memory could show you the change history but would require traversing the entire log to answer a simple question about the current state.

Together, they enable Veridia to serve both operational queries that need immediate answers and investigative queries that need complete context. The LLM cognitive layer chooses which memory mode to use based on the nature of the user's question.

---

## Truth States

A truth state is a snapshot of all knowledge at a specific version. It represents the complete, internally consistent set of facts that were simultaneously true at that point in the knowledge timeline.

### What a Truth State Contains

A truth state is a mapping from knowledge atom identifiers to their values. If an atom exists at that version, its value is present. If an atom does not yet exist or has been deleted, it is absent. There is no ambiguity and no partial presence. At version v, an atom either has a specific value or it does not exist.

A truth state is self-contained. It does not reference other versions. It does not contain pointers to the deltas that produced it. It is a pure representation of facts at a moment, suitable for direct consumption by the LLM cognitive layer.

### Immutability of Historical States

Once a truth state at version v has been reconstructed, it never changes. New deltas appended to the log create new versions and new truth states. They do not alter previously reconstructed states. Version v1.0 of the retention policy specified 90 days. After version v2.0 changes the value to 30 days, the truth state at v1.0 still specifies 90 days. It always will.

This immutability is not a cache invalidation strategy. It is a logical property of the memory model. Since deltas are never modified and the reconstruction function is deterministic, the same version always produces the same state. Historical truth is as stable as the delta log itself.

### Current Truth

The current truth is the truth state at the highest version tag in the delta log. It represents the system's best knowledge at the present moment. It changes when new deltas are appended. It is the default retrieval target for queries that do not specify a version.

Current truth is not special in structure. It is simply the most recent truth state. The same reconstruction process that produces any historical state produces the current state. There is no separate "current state" storage. There is only the delta log and the states derived from it.

### Historical Truths

A historical truth is any truth state at a version tag earlier than the current one. The system can reconstruct any historical truth on demand by applying only the deltas up to the requested version. A query about "the policy as of May 1, 2025" resolves to a specific version tag, and the system reconstructs the truth state at that version.

Historical truths enable point-in-time queries without maintaining separate snapshots. The delta log contains all the information needed to reconstruct any past state. The system does not need to anticipate which historical versions will be queried. It can reconstruct any version that has ever existed.

---

## Deltas

A delta is the bridge between truth states. It records a single, atomic modification to a single knowledge atom. It is the fundamental unit of change in Veridia's memory model.

### Deltas as State Transitions

Every modification to knowledge produces a delta. When a document updates the data retention period from 90 days to 30 days, that change is recorded as a delta. The delta captures what atom changed, what the new value is, what the previous value was, and what caused the change. It carries a version tag that positions it in the ordered sequence of all changes.

A delta is not a document. It does not contain the full text of the policy that triggered the change. It contains the logical effect of that policy on the system's knowledge. If a document changes three different facts, it produces three deltas — one per atom. If a document is analyzed and found to change nothing, it may produce a no-op delta that records the analysis without modifying any values.

### Causal Preservation

Every delta preserves the causal trigger that produced it. The system knows not only that the retention period changed from 90 days to 30 days, but that it changed because of a compliance review documented in a specific policy update. This causal information is not metadata. It is a structural element of the delta. Without it, the system could answer "what changed?" but not "why?"

The cause travels with the delta through all memory operations. When episodic memory returns a trajectory, each delta in the sequence includes its cause. When the LLM synthesizes a response explaining a change, the cause is available for inclusion in the explanation. Causality is not inferred from document comparison. It is explicitly recorded at ingestion time.

### No Overwrite, No Deletion

Deltas never overwrite history. A correction to a previous value does not modify the original delta. It produces a new delta that supersedes the original in the truth state but preserves the original in the episodic record. The incorrect value, the fact that it was incorrect, and the correction that fixed it are all preserved.

This property is essential for auditability. An auditor investigating a decision made in January needs to know what the system believed in January, even if that belief was later corrected. The delta log preserves the full history of knowledge — including knowledge that was later found to be wrong.

---

## Knowledge Evolution

Knowledge in Veridia evolves through a continuous sequence of states and transitions. The pattern is simple and uniform: truth state, delta, truth state, delta, truth state. There is no other mechanism of change.

The process begins with an empty initial state. No atoms exist. No facts are known. The first document enters the system and is transformed into deltas. Each delta sets the value of one atom. The truth state after applying those deltas contains the facts introduced by that document.

A second document arrives. It is analyzed against the current truth state. The analysis determines which atoms it affects and how. It produces deltas that modify existing atoms, introduce new ones, or retract obsolete ones. Those deltas are appended to the log. The truth state advances to the next version.

This cycle repeats indefinitely. Each document produces deltas. Each delta advances the state. The delta log grows monotonically. The current truth state reflects the cumulative effect of every document ingested so far. Historical truth states remain available for any version that ever existed.

The evolution is explicit. There is no ambiguity about what changed between version v1.0 and version v2.0. The deltas between them are the complete and precise record of the difference. There is no need to diff documents, compare timestamps, or infer what might have changed. The system recorded it directly.

---

## State Reconstruction

State reconstruction is the process of deriving a truth state from the delta log. It is the mechanism that connects the episodic record to the semantic view.

### Conceptual Process

To reconstruct the truth state at version v, the system begins with the empty initial state. It then applies every delta with a version tag less than or equal to v, in version order. Each delta modifies the state by setting, modifying, or deleting the value of its target atom. After the last applicable delta is applied, the resulting state is the truth state at version v.

This process is purely conceptual. Implementations may cache intermediate states, apply deltas incrementally, or use other optimizations. The architecture requires only that the result be identical to what would be produced by replaying the full log from the beginning.

### Reconstructing Any Version

The reconstruction process works identically for any version — current or historical. To reconstruct the state at v1.0, apply all deltas up to v1.0. To reconstruct the state at v5.0, apply all deltas up to v5.0. The process does not require that intermediate states be materialized. It does not require that versions be contiguous. Any version tag that exists in the log can be reconstructed on demand.

This property enables point-in-time queries without precomputation. The system does not need to know in advance which historical versions will be queried. It does not need to store snapshots at regular intervals. The delta log contains sufficient information to reconstruct any version that has ever existed, at any time.

---

## Deterministic Memory

The Veridia memory model is fully deterministic. Given the same initial state and the same delta log, state reconstruction always produces the same truth state. There is no randomness, no ranking, no probabilistic selection, and no dependence on external state.

### Why Determinism Matters

Determinism enables three properties that are essential to the architecture's value.

First, reproducibility. The same query at the same version always produces the same answer. Two independent systems with the same delta log will produce identical responses to the same questions. This enables testing, validation, and independent verification of results.

Second, auditing. An auditor can verify that a response was correct by reconstructing the relevant truth state and confirming that it contains the facts that were reported. The auditor does not need to trust the system. They can replay the delta log and verify the result independently.

Third, explainability. When the system provides an answer, it can trace that answer to the specific deltas that produced the relevant facts. The trace is not a heuristic approximation. It is a direct consequence of the deterministic reconstruction process. The facts in the response correspond exactly to the deltas that set them.

### The Boundary of Determinism

The memory model is deterministic. The LLM cognitive layer that interprets queries and synthesizes natural language responses is not. This boundary is explicit in the architecture. The facts retrieved from Veridia are deterministic and verifiable. The natural language that wraps those facts may vary. The architecture guarantees that the facts are correct, not that the prose is identical.

---

## Architectural Guarantees

The memory model provides the following guarantees. Each follows from the structure described in this document and the principles established in previous documents.

**Immutable history.** Once a delta is stored, it is never modified, deleted, or reordered. The full history of knowledge evolution is permanently preserved. Corrections arrive as new deltas that reference the ones they supersede.

**Explicit evolution.** Every change to knowledge is recorded as an explicit delta with a version tag, a target atom, old and new values, and a causal trigger. There is no implicit change. There is no change that occurs without leaving a record.

**Deterministic reconstruction.** Given the same delta log, the same version always reconstructs to the same truth state. This holds across implementations, across restarts, and across independent deployments with identical data.

**Temporal consistency.** A query at version v returns only facts that were simultaneously true at version v. The system cannot accidentally combine facts from different versions. If the user asks for a cross-version comparison, the versions are explicitly labeled.

**Complete traceability.** Every fact in a truth state can be traced to the specific delta that most recently set its value. Every delta can be traced to the document or event that triggered it. The full causal chain from query response back to source document is preserved.

**Separation of facts and history.** Semantic memory provides facts without provenance for efficient access. Episodic memory provides provenance without requiring traversal of the full history for simple queries. Both derive from the same immutable log, ensuring consistency between them.

**Document independence.** After ingestion, the original documents are not required for any memory operation. Retrieval, reconstruction, and query resolution operate entirely from the delta log. The documents may be archived or discarded without affecting the system's ability to answer queries.

---

## Relationship to Other Documents

| Document | Relationship |
|---|---|
| [02 — Design Philosophy](./02-design-philosophy.md) | Motivates why the memory model separates semantic and episodic memory |
| [03 — Architectural Principles](./03-architectural-principles.md) | Establishes the guarantees this memory model must provide |
| [04 — Core Concepts](./04-core-concepts.md) | Provides formal definitions of delta, truth state, atom, trajectory, and related terms |
| [06 — Delta Schema](./06-delta-schema.md) | Specifies the exact structure of deltas stored in the log |
| [07 — Retrieval Model](./07-retrieval-model.md) | Defines how queries access semantic and episodic memory |

---

## Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-07-01 | Initial release |

# Truth State

| Concept | Description | Architectural Role |
|---|---|---|
| Truth State | A complete snapshot of all facts simultaneously true at a specific version | The unit of knowledge retrieval; what semantic memory returns |
| Current Truth | The truth state at the highest version tag in the delta log | Default retrieval target for queries without temporal qualification |
| Historical Truth | Any truth state at a version tag earlier than the current one | Enables point-in-time queries about past states of knowledge |
| Immutable State | Once reconstructed, a truth state at version v never changes | Guarantees that historical queries remain stable regardless of new deltas |

---

# Memory Layers

| Layer | Stores | Primary Purpose |
|---|---|---|
| Semantic Memory | Facts without history — the net result of all deltas at a version | Answer "What is true?" efficiently without provenance overhead |
| Episodic Memory | Ordered deltas with causes, timestamps, and previous values | Answer "What happened and why?" with full causal context |

---

# Delta Characteristics

| Property | Meaning | Why It Matters |
|---|---|---|
| Immutable | Once stored, a delta is never modified or deleted | Preserves the full history of knowledge, including corrections |
| Versioned | Every delta carries a version tag that positions it in the sequence | Enables reconstruction of any historical state |
| Causal | Every delta records the trigger that produced it | Answers not just "what changed?" but "why?" |
| Ordered | Deltas form a totally ordered sequence by version tag | Guarantees deterministic reconstruction of any state |
| Traceable | Every delta can be traced back to its source document | Provides complete audit trail from fact to origin |

---

# Knowledge Evolution

| Stage | Description |
|---|---|
| Initial Truth State | The empty state before any deltas are applied; no atoms exist |
| Delta Applied | A single delta modifies one atom, recording the change and its cause |
| New Truth State | The result of applying the delta to the previous state; the atom now has a new value |
| Historical Preservation | Previous truth states remain accessible; the delta log retains all versions |

---

# State Reconstruction

| Input | Process | Output |
|---|---|---|
| Empty initial state plus delta log | Apply all deltas with version tag ≤ target version, in order | Truth state at the target version |
| Previously reconstructed state plus new deltas | Apply only deltas with version tags since the last reconstruction | Updated truth state without replaying full log |
| Delta log plus specific version tag | Filter deltas by version, apply sequentially to initial state | Historical truth state at the requested version |

---

# Deterministic Guarantees

| Guarantee | Explanation |
|---|---|
| Determinism | Same delta log plus same version always produces identical truth state |
| Reproducibility | Two independent systems with the same delta log produce identical query responses |
| Temporal Consistency | A query at version v returns only facts simultaneously true at version v |
| Auditability | Any response can be verified by reconstructing the relevant state and comparing |
| Explainability | Every fact can be traced to the specific delta and cause that produced it |

---

# Memory Model Summary

| Component | Responsibility |
|---|---|
| Truth State | Represents all facts simultaneously true at a specific version |
| Delta | Records a single atomic change to one knowledge atom with its cause |
| Semantic Memory | Provides efficient access to facts without provenance |
| Episodic Memory | Provides ordered change history with full causal attribution |
| Trajectory | The ordered sequence of deltas affecting a single atom across versions |
| Current Truth | The truth state at the latest version; reflects all ingested knowledge |
| Historical Truth | Any past truth state; reconstructible on demand from the delta log |