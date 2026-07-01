# 01 — Vision

**Version:** 1.0.0
**Status:** Stable
**Last Updated:** 2026-07-01

---

## Purpose of This Document

This document defines the architectural vision for Veridia. It does not describe how Veridia works. It describes **what Veridia is for**, **what problems it addresses**, and **what constraints shape its design**.

Every architectural decision in subsequent documents traces back to a principle or constraint established here.

This document serves as:

- The entry point for new contributors to understand the project's purpose
- The reference for evaluating whether a proposed feature aligns with the architecture
- The foundation that all Architecture Decision Records (ADRs) reference

---

## What Veridia Is

Veridia is a **versioned, causality-aware memory architecture** for systems where knowledge changes over time and the evolution of truth matters as much as the truth itself.

It is not:

- A retrieval-augmented generation (RAG) framework
- A vector database
- A knowledge graph
- An embedding pipeline
- A general-purpose search system

It is a **memory model** — a way of organizing, storing, and retrieving knowledge that treats time, causality, and versioning as structural properties rather than optional metadata.

---

## The Core Insight

Most retrieval systems treat knowledge as a static collection of documents. When knowledge changes, new documents enter the index alongside old ones. The system has no structural understanding that one document supersedes another.

Veridia is built on a different insight:

> **A document is not knowledge. A document is evidence of a change in knowledge.**

When a regulation is amended, the amendment document is not the knowledge. The amendment is evidence that a specific fact changed from one value to another at a specific time for a specific reason.

Veridia extracts the **delta** — the transition between states — and stores that as the primary unit of knowledge. The original document may be discarded. What remains is an ordered, causal, versioned record of how truth evolved.

---

## The Problems Veridia Addresses

### Problem 1: Version Mixing

Retrieval systems that index multiple versions of the same logical content cannot distinguish between superseded and current information. A query returns semantically similar chunks from different versions, leaving the user to resolve contradictions.

### Problem 2: Missing Provenance

Even when a system returns the correct version, it cannot explain when that version became true, what it replaced, or why it changed. The causal history of knowledge is absent from the index.

### Problem 3: Temporal Inconsistency

Retrieval systems may combine facts that were never simultaneously true. A response might mix a policy from January, a price from March, and a procedure from June — describing a state that never existed.

These problems are structural, not incidental. They arise because the storage model treats all content as an undifferentiated set. Mitigations like metadata filters and recency ranking reduce symptoms but do not address the underlying cause.

---

## Design Goals

Veridia is designed to satisfy the following goals, in priority order:

### G1 — Temporal Consistency

A query specifying a point in time must return only facts that were simultaneously true at that point. The system must guarantee that no response combines facts from different temporal states unless explicitly requested.

### G2 — Causal Traceability

Every fact in the system must be traceable to the delta that introduced it, the delta that modified it (if any), and the causal trigger that produced each change. The system must be able to answer: "What changed, when, and why?"

### G3 — Deterministic Reconstruction

Given the same initial state and the same sequence of deltas, the system must always reconstruct the same truth state. There is no randomness, ranking, or probabilistic retrieval in state reconstruction.

### G4 — Auditability

Every query response must be reproducible. Given the same query and the same system state, the system must produce the same response. Every response must be traceable to the exact deltas that produced it.

### G5 — Operational Simplicity

The system must not require vector databases, embedding models, similarity indexes, or continuous re-indexing pipelines. Storage and retrieval must operate on structured, versioned records.

### G6 — LLM Compatibility

The memory model must produce structured outputs that a language model can consume directly for interpretation, navigation, and synthesis. The LLM is the cognitive layer; Veridia is the memory layer. The interface between them must be explicit and stable.

---

## Design Constraints

The following constraints are accepted as inherent to the architecture:

### C1 — Atom-Identifiable Knowledge Required

Veridia requires that knowledge can be decomposed into identifiable, persistent atoms. If a domain's knowledge cannot be expressed as discrete facts with stable identity, Veridia is not appropriate.

### C2 — Higher Ingestion Cost

Converting documents to deltas requires more computation at ingestion time than chunking and embedding. This is a deliberate tradeoff: ingestion cost is exchanged for retrieval determinism and temporal consistency.

### C3 — Constrained Query Flexibility

Veridia does not support open-ended semantic search ("find documents similar to this idea"). Queries must resolve against known atoms and version states. This is a feature, not a limitation — the constraint enables the guarantees the architecture provides.

### C4 — Not a Drop-in Replacement

Veridia is not designed to replace existing RAG pipelines. It is designed for a specific subset of use cases where temporal consistency and causal traceability are required. It coexists with other retrieval architectures.

---

## Scope

### In Scope

- Defining the delta as the fundamental unit of knowledge modification
- Defining truth states and state reconstruction semantics
- Defining version tags and temporal ordering guarantees
- Defining retrieval by state and trajectory
- Defining the LLM integration interface
- Providing reference implementations of core abstractions

### Out of Scope (MVP)

- Distributed delta logs and multi-node consensus
- Real-time streaming ingestion
- Automatic atom extraction from unstructured text
- Natural language query parsing (the LLM layer handles this)
- Production storage backends
- Performance optimization
- Branching and merging of knowledge versions

---

## Relationship to Other Architectural Documents

This document establishes the vision. Subsequent documents derive from it:

| Document | Purpose |
|---|---|
| **02 — Core Concepts** | Formal definitions of delta, truth state, atom, trajectory, version tag, semantic memory, episodic memory |
| **03 — Delta Schema** | Delta structure, field specifications, validation rules |
| **04 — State Model** | State reconstruction algorithm, deterministic guarantees |
| **05 — Retrieval Model** | Semantic vs episodic retrieval, query resolution, response synthesis |
| **06 — LLM Interface** | Contract between Veridia memory layer and LLM cognitive layer |
| **07 — Storage Backend** | Delta log requirements, immutability guarantees, append semantics |
| **ADRs/** | Architecture Decision Records for specific design choices |

---

## What Veridia Is Not

To prevent scope creep and architectural confusion:

- **Not a RAG framework.** Veridia does not perform document chunking, embedding, or similarity search.
- **Not a vector database.** Veridia does not store, index, or query embedding vectors.
- **Not a knowledge graph.** Veridia does not model entities and relationships in a graph structure. Atoms are discrete facts, not nodes with edges.
- **Not a general-purpose database.** Veridia is a specialized memory model for versioned knowledge, not a transactional or analytical database.
- **Not Event Sourcing, but related.** Veridia shares structural similarities with Event Sourcing (append-only log, state reconstruction) but differs in domain: Veridia's deltas are designed for LLM consumption and carry causal context specific to knowledge evolution.

---

## Success Criteria

The Veridia MVP will be considered successful when:

1. A user can ingest two versions of a document and query the truth state at any point between them
2. A query at a specific version returns only facts true at that version
3. A trajectory query returns the ordered sequence of changes with causal attribution
4. State reconstruction is deterministic: same inputs always produce same outputs
5. The system operates without a vector database, embedding model, or similarity index
6. The LLM interface is documented and implementable with any LLM that supports structured output

---

## References

- [Veridia README](../README.md) — Project overview
- [02 — Core Concepts](./02-core-concepts.md) — Formal definitions
- [ADRs](./adrs/) — Architecture Decision Records