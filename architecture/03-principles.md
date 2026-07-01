# 03 — Architectural Principles

**Version:** 1.0.0  
**Status:** Stable  
**Last Updated:** 2026-07-01  
**Depends On:** [01 — Vision](./01-vision.md), [02 — Design Philosophy](./02-design-philosophy.md)

---

## Purpose of This Document

This document defines the architectural principles that govern every technical decision in Veridia. While the Design Philosophy explains **why** the architecture makes certain choices, this document specifies **what rules** those choices must follow.

Each principle is:

- **Actionable:** It can be used to evaluate a design decision, code change, or feature proposal
- **Verifiable:** Conformance can be tested, measured, or reviewed
- **Ranked:** When principles conflict, higher-priority principles take precedence

This document serves as the reference for code reviews, architecture discussions, and contribution evaluation.

---

## Principle Hierarchy

Principles are organized into three tiers:

| Tier | Scope | Principles |
|---|---|---|
| **Tier 1 — Foundational** | Cannot be violated without breaking the architecture's core guarantees | P1, P2, P3, P4 |
| **Tier 2 — Structural** | Define how the architecture operates; violations degrade but do not destroy guarantees | P5, P6, P7, P8 |
| **Tier 3 — Operational** | Define quality and maintainability standards; violations increase technical debt | P9, P10, P11, P12 |

---

## Tier 1 — Foundational Principles

---

### P1 — Temporal Consistency

**Rule:** A query that specifies a version tag must return only facts that were simultaneously true at that version.

**Definition:** Given a version tag `v`, the set of facts returned by any query scoped to `v` must be a subset of the truth state `S(v)` reconstructed from all deltas with version tag ≤ `v`.

**Verification:**
- For any query with explicit or implicit version tag `v`, all returned facts must have `effective_version ≤ v`
- For any returned fact, there must exist no delta with tag ≤ `v` that retracts or modifies that fact to a different value
- Cross-version queries must explicitly label which facts belong to which version

**Violation Example:** A query for "current policy" returns the retention period from v2.0 and the encryption standard from v1.0 without indicating the version mismatch.

**Priority Justification:** This is the architecture's primary guarantee. Without temporal consistency, Veridia offers no advantage over traditional retrieval systems.

---

### P2 — Deterministic State Reconstruction

**Rule:** Given identical inputs, state reconstruction must always produce identical outputs.

**Definition:** Let `R(S₀, [δ₁, ..., δₙ])` be the state reconstruction function where `S₀` is the initial state and `[δ₁, ..., δₙ]` is an ordered sequence of deltas. For any two invocations with the same `S₀` and the same delta sequence in the same order, `R` must produce the same truth state `Sₙ`.

**Verification:**
- Run state reconstruction twice on the same delta log; compare resulting states bit-for-bit
- Reconstruction must not depend on system time, random number generation, external services, LLM calls, or any non-deterministic input
- The reconstruction algorithm must be documented and independently implementable

**Violation Example:** Using an LLM to resolve conflicts between deltas during reconstruction. LLM outputs are non-deterministic by nature.

**Priority Justification:** Determinism enables auditability, reproducibility, and independent verification. It is the foundation of trust in the system.

---

### P3 — Delta Immutability

**Rule:** Once stored, a delta must never be modified, deleted, reordered, or overwritten.

**Definition:** A delta `δ` with version tag `v` that has been appended to the delta log is permanently fixed. Corrections, retractions, and amendments arrive as new deltas with higher version tags. The original delta remains in the log and remains retrievable.

**Verification:**
- The storage layer must expose no update or delete operations on deltas
- The version tag of a stored delta must be impossible to change
- Historical states reconstructed before a correction must still be reconstructable after the correction

**Violation Example:** A correction to a policy value directly edits the original delta's value field rather than creating a new delta.

**Priority Justification:** Immutability preserves the full causal history. Without it, historical queries become unreliable and audit trails become incomplete.

---

### P4 — Causal Attribution

**Rule:** Every delta must record the causal trigger that produced it.

**Definition:** A delta must include a `cause` field that identifies the event, document, decision, or correction that triggered the state transition. The cause must be sufficiently specific that a human reader can understand why the change occurred.

**Verification:**
- Every delta in the log must have a non-empty `cause` field
- The cause must reference an identifiable trigger (document ID, event type, correction reason, author, timestamp)
- Trajectory queries must return causes alongside value changes

**Violation Example:** A delta records that the retention period changed from 90 to 30 days but provides no cause. The system cannot answer "why did this change?"

**Priority Justification:** Causality enables provenance queries. Without it, the system can answer "what changed?" but not "why?" — losing half its value proposition.

---

## Tier 2 — Structural Principles

---

### P5 — Atom Identity Persistence

**Rule:** A knowledge atom must maintain the same identifier across all versions, regardless of how many times its value changes.

**Definition:** A knowledge atom `A` with identifier `id_A` represents the same logical fact at every version. When a delta modifies `A`'s value from `v₁` to `v₂`, the delta references `id_A`. The atom does not receive a new identifier.

**Verification:**
- For any atom, querying its trajectory must return all deltas that reference that atom's identifier
- Two deltas that modify the same logical fact must reference the same atom identifier
- Atom identifiers must be stable across system restarts, reingestion, and schema evolution

**Violation Example:** Each version of a policy assigns a new UUID to "data_retention_period," making it impossible to trace the atom's history.

**Priority Justification:** Without identity persistence, trajectories cannot be constructed. The system cannot answer "how has this fact changed over time?"

---

### P6 — Retrieval by State Lookup

**Rule:** Retrieval must operate by state lookup, not by similarity search.

**Definition:** When resolving a query, the system must:
1. Identify the target knowledge atom(s) and version tag
2. Reconstruct the truth state at that version
3. Return the atom values from that state

At no point in the retrieval path may vector similarity, embedding distance, or probabilistic ranking be used to select or order results.

**Verification:**
- The retrieval code path must contain no calls to embedding APIs, vector databases, or similarity functions
- The same query with the same atom and version must always return the same result
- Retrieval latency must not depend on corpus size in a way characteristic of similarity search

**Violation Example:** Retrieving "similar" atoms to expand query coverage using cosine similarity on atom embeddings.

**Priority Justification:** State lookup is what enables deterministic retrieval and temporal consistency. Similarity search reintroduces the ambiguity the architecture exists to eliminate.

---

### P7 — Document Independence After Ingestion

**Rule:** After transformation, the system must not depend on the original document for retrieval.

**Definition:** Once a document has been transformed into deltas and those deltas have been validated and stored, the retrieval path must reference only deltas and reconstructed states. The original document text must not be retrieved, chunked, embedded, or included in LLM context.

**Verification:**
- Delete all ingested documents after transformation; verify that all queries continue to return correct results
- The retrieval code path must contain no references to document storage or document retrieval
- LLM context must be constructed from structured state data, not from document text

**Violation Example:** Retrieving the original document chunk and including it in the LLM prompt alongside the delta-extracted facts.

**Priority Justification:** If the system depends on original documents, it inherits all the version mixing and temporal inconsistency problems of document-based retrieval. The delta transformation must be the single point of knowledge extraction.

---

### P8 — Structured LLM Interface

**Rule:** All communication between Veridia's memory layer and the LLM cognitive layer must use structured, typed data.

**Definition:** The output of every retrieval operation must be a structured object with typed fields (atom identifiers, values, version tags, causes). The LLM must not be expected to parse natural language from Veridia. The LLM's prompts are part of the cognitive layer implementation, not the memory layer architecture.

**Verification:**
- Retrieval operations must return data in a schema-defined format (JSON, Protocol Buffers, or similar)
- The memory layer must expose no natural language generation capability
- The interface between memory and cognitive layers must be documented as a contract

**Violation Example:** Veridia returns a natural language paragraph describing the current state, and the LLM must re-extract facts from it.

**Priority Justification:** A structured interface enables independent evolution of the memory and cognitive layers. It also enables non-LLM consumers (audit tools, debuggers, test harnesses) to interact with Veridia.

---

## Tier 3 — Operational Principles

---

### P9 — Append-Only Storage Model

**Rule:** The delta log must support only append operations. No in-place modification, deletion, or reordering of stored deltas.

**Definition:** The storage layer must expose an interface that allows adding new deltas and reading existing deltas in version order. Update and delete operations must not exist in the storage interface.

**Verification:**
- The storage interface must have no method signatures for update or delete
- Attempting to modify a stored delta must result in an error at the API level
- The delta log must be readable in version order without external sorting

**Violation Example:** A storage backend that allows updating a delta's cause field after storage.

**Priority Justification:** This operationalizes P3 (Delta Immutability) at the storage layer.

---

### P10 — Schema-Versioned Deltas

**Rule:** The delta schema must include a version identifier to allow evolution of the delta format over time.

**Definition:** Each delta must carry a `schema_version` field indicating which version of the delta schema it conforms to. The state reconstruction engine must be able to process deltas with different schema versions in the same log.

**Verification:**
- Every stored delta must have a parseable `schema_version` field
- Adding a new field to the delta schema must not break reconstruction of historical states
- Schema version must be independent of knowledge version tag

**Violation Example:** A new required field is added to the delta schema, making all previously stored deltas invalid.

**Priority Justification:** Schema evolution is inevitable in a long-lived system. Without explicit versioning, schema changes require destructive migrations.

---

### P11 — Observable State Reconstruction

**Rule:** Every state reconstruction operation must produce observable artifacts suitable for debugging, auditing, and testing.

**Definition:** The reconstruction path must support:
- Logging which deltas were applied and in what order
- Exporting intermediate states at each version
- Validating that the final state matches a known checksum or expected value
- Tracing a specific fact in the final state back to the delta that produced it

**Verification:**
- Enable debug logging and verify that each applied delta is recorded with its version tag and effect
- Export a truth state and independently verify its contents
- Given a fact from a query response, identify the exact delta that introduced or last modified it

**Violation Example:** State reconstruction runs as an opaque process with no logging, making it impossible to debug incorrect query results.

**Priority Justification:** Observability enables trust. Without it, deterministic reconstruction is a claim, not a verifiable property.

---

### P12 — Testable Determinism

**Rule:** The determinism of state reconstruction must be verifiable through automated tests, not just documentation claims.

**Definition:** The test suite must include:
- Tests that reconstruct the same state twice and assert bit-for-bit equality
- Tests that reconstruct states on different machines and assert identical results
- Tests that add new deltas and verify that prior states remain unchanged
- Tests that verify determinism after schema migration

**Verification:**
- Run the determinism test suite; all tests must pass
- Introduce a non-deterministic operation (e.g., timestamp injection) and verify that a test catches it
- Tests must be part of CI pipeline and block merges on failure

**Violation Example:** Determinism is stated in documentation but no automated test verifies it.

**Priority Justification:** Undetected non-determinism silently corrupts the architecture's primary guarantee. Automated verification is the only reliable safeguard.

---

## Principle Interaction and Conflict Resolution

When principles appear to conflict, apply the following resolution rules:

| Conflict | Resolution | Rationale |
|---|---|---|
| P6 (State Lookup) vs. user desire for fuzzy search | P6 takes precedence | Fuzzy search can be implemented in the cognitive layer after deterministic retrieval |
| P1 (Temporal Consistency) vs. cross-version comparison queries | Cross-version queries are permitted if each fact is labeled with its version | The guarantee applies per-fact, not per-response |
| P3 (Immutability) vs. storage cost concerns | P3 takes precedence | Storage is cheap; lost history is irrecoverable |
| P8 (Structured Interface) vs. LLM optimization | P8 takes precedence | The interface contract must be stable; LLM prompt optimization is a cognitive layer concern |
| P4 (Causal Attribution) vs. automated ingestion without cause metadata | Ingestion must be rejected or enriched | A delta without a cause violates Tier 1; the system must not accept it |

---

## Compliance Checklist

Use this checklist when evaluating a new feature, code change, or architectural proposal:

### Tier 1 — Must Pass All

- [ ] **P1:** Does the change guarantee that queries return only facts simultaneously true at the queried version?
- [ ] **P2:** Is state reconstruction fully deterministic with the same inputs?
- [ ] **P3:** Are stored deltas never modified, deleted, or reordered?
- [ ] **P4:** Does every delta record its causal trigger?

### Tier 2 — Must Pass All

- [ ] **P5:** Do knowledge atoms maintain identity across all versions?
- [ ] **P6:** Does retrieval use state lookup, not similarity search?
- [ ] **P7:** Does retrieval depend only on deltas, not original documents?
- [ ] **P8:** Is the LLM interface structured and typed?

### Tier 3 — Should Pass All; Exceptions Require Justification

- [ ] **P9:** Is storage append-only with no update/delete operations?
- [ ] **P10:** Does the delta schema include a version identifier?
- [ ] **P11:** Is state reconstruction observable and debuggable?
- [ ] **P12:** Is determinism verified by automated tests?

---

## Relationship to Other Documents

| Document | Relationship |
|---|---|
| [01 — Vision](./01-vision.md) | Defines the problems and goals these principles serve |
| [02 — Design Philosophy](./02-design-philosophy.md) | Explains why these principles were chosen |
| [04 — Delta Schema](./04-delta-schema.md) | Derives delta structure from P3, P4, P5, P10 |
| [05 — State Model](./05-state-model.md) | Derives reconstruction algorithm from P1, P2, P11, P12 |
| [06 — Retrieval Model](./06-retrieval-model.md) | Derives retrieval semantics from P6, P7, P8 |
| [ADRs](./adrs/) | Records specific decisions evaluated against these principles |

---

## Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-07-01 | Initial release |