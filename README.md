# Veridia v1

**A versioned, causality-aware memory architecture for systems where knowledge changes.**

---

Veridia is a memory architecture designed for language model systems that must track how facts evolve over time. It stores knowledge as explicit, ordered state transitions rather than as documents or embedding vectors. This structural difference enables retrieval that respects *when* something was true and *why* it changed.

The project is in active development as an MVP (Minimum Viable Product). This README describes the architecture, the concepts it rests on, and the tradeoffs it makes.

---

## Contents

- [The Problem](#the-problem)
- [Design Philosophy](#design-philosophy)
- [Core Concepts](#core-concepts)
- [High-Level Architecture](#high-level-architecture)
- [Simple Example](#simple-example)
- [Architectural Principles](#architectural-principles)
- [Advantages](#advantages)
- [Limitations](#limitations)
- [Benchmarks](#benchmarks)
- [Repository Structure](#repository-structure)
- [Roadmap](#roadmap)
- [Citation](#citation)
- [License](#license)

---

## The Problem

Retrieval-augmented generation systems and knowledge graphs operate on a deceptively simple assumption: that the information they index represents a coherent body of knowledge. When the underlying knowledge changes, that assumption breaks down.

### The Nature of Evolving Knowledge

Knowledge in most domains is not static. Regulations are amended. Contracts are renegotiated. APIs are deprecated and replaced. Technical documentation tracks software versions that ship weekly. Scientific consensus shifts as new studies replicate or contradict prior findings. Organizational policies change with leadership, compliance reviews, and external audits.

Each change produces a new document or a revised version of an existing one. Over time, a corpus accumulates multiple versions of the same logical information. A data retention policy might exist in three versions across two years. A pricing table might have monthly snapshots. A security protocol might fork into regional variants.

Retrieval systems are typically designed for corpora that grow by *addition*, not by *replacement*. When new information supersedes old information, the system has no structural way to express that relationship. The old document and the new document sit side by side in the index. The retrieval layer treats them as independent items, ranked by their individual similarity to the query.

This creates three distinct failure modes.

### Failure Mode 1 — Version Mixing

When a user queries a system that indexes multiple versions of the same logical content, the retrieval step may return chunks from different versions in the same result set. A query about data retention might retrieve a paragraph from the 2023 policy alongside a sentence from the 2025 update, presented as equally relevant.

The user receives contradictory information with no indication of which version is authoritative. If the 2023 policy specified 90 days and the 2025 update reduced it to 30 days, both numbers appear in the context window. The language model generating the final response may synthesize them, pick one arbitrarily, or present both without resolution.

**Example.** A compliance officer queries: "What is our current data retention period for user logs?" The retrieval step returns:

- Chunk A (from Policy v1, January 2023): "User activity logs must be retained for a period of 90 days."
- Chunk B (from Policy v2, March 2025): "User activity logs must be retained for a period of 30 days from the date of collection."

Both chunks match the query semantically. The system has no mechanism to determine that Chunk B supersedes Chunk A. The officer receives an ambiguous answer or, worse, a confident synthesis of both.

### Failure Mode 2 — Missing Provenance

Even when a retrieval system returns a single, correct version of a fact, it rarely explains *how* that fact came to be true. The retrieved chunk contains the current value but not its history.

This matters when the user's question is not "what is true?" but "when did this become true, what did it replace, and why?" These questions arise in audits, incident investigations, legal discovery, and regulatory reviews.

A system that stores only the current state cannot answer them. A system that stores all versions but does not link them causally can answer "what were the values?" but not "what triggered the change?"

**Example.** An engineer investigating a production incident asks: "When was the connection timeout changed from 30 seconds to 5 seconds, and who authorized it?" The retrieval system returns the current configuration showing a 5-second timeout. It may also return an earlier document showing a 30-second timeout. But it cannot connect them: it cannot state that the change occurred on a specific date, in response to a specific change request, replacing a specific prior value. The causal relationship is absent from the index.

### Failure Mode 3 — Temporal Inconsistency

The most subtle failure occurs when a retrieval system combines facts that were never simultaneously true. A single query may retrieve multiple chunks, each factually correct at some point in time, but together describing a state that never existed.

This happens because retrieval treats each chunk as an independent relevance match. There is no guarantee that all chunks returned for a query were valid at the same moment. The system retrieves the most semantically similar content for each part of the query, even if those pieces of content were true months apart.

**Example.** A financial analyst queries: "What are the fees for international transfers above $10,000?" The retrieval step returns:

- Chunk A (Fee Schedule Q1 2025): "International transfers above $10,000 incur a flat fee of $45."
- Chunk B (Policy Update Q2 2025): "The minimum threshold for international transfer fees has been raised to $25,000."

Individually, both chunks are factually correct. But they were never true at the same time. In Q1, transfers above $10,000 cost $45. In Q2, transfers below $25,000 incur no fee. The combination—"transfers above $10,000 cost $45, but the minimum threshold is $25,000"—describes a logically inconsistent policy that never existed. The language model may surface this contradiction or, worse, smooth it over into a confident but incorrect answer.

### Why This Matters

These failure modes are not theoretical edge cases. They surface reliably in any domain where the *applicable version* of a fact depends on a point in time.

- **Compliance and audit.** An auditor must determine what policy was in effect on the date of a transaction, not what policy is current or what policies happen to match semantically.
- **Legal reasoning.** A contract clause amended six months ago has no legal force in its original form. Retrieving the original alongside the amendment creates misrepresentation.
- **Healthcare and regulatory environments.** Treatment protocols, drug approvals, and safety guidelines change. A retrieval system that mixes versions risks providing clinically incorrect guidance.
- **Scientific research.** A meta-analysis must track how findings evolved, which studies superseded which, and whether a conclusion holds across versions of the evidence base.

In each case, correctness depends not only on retrieving relevant information but on retrieving information that was *simultaneously valid* at the relevant point in time.

### Existing Mitigations

Many retrieval pipelines attempt to address these problems through post-hoc mechanisms. Metadata filters restrict retrieval to documents within a date range. Timestamp annotations on chunks allow re-ranking by recency. Hybrid systems combine vector search with keyword filters on version numbers. Some pipelines use the LLM itself to detect and reconcile contradictions in the retrieved context.

These approaches reduce the frequency of version mixing and temporal inconsistency, but they do not eliminate the underlying structural cause. They operate at the retrieval or post-retrieval stage, on top of a storage model that treats all indexed content as an undifferentiated set. The relationship between versions—what supersedes what, what caused a change, what a value was before it changed—remains implicit in the documents themselves, extracted heuristically if at all.

---

## Design Philosophy

Veridia is built on a single architectural decision: **model truth states, not documents.**

A document is a container of information at a moment in time. When the world changes, a new document appears. Traditional retrieval treats these as independent items, leaving the relationship between them implicit or inferred.

Veridia instead stores the *transition* between knowledge states—a structured record of what changed, when, and what caused the change. The document is ingested, converted into one or more deltas, and then may be discarded. Queries resolve against reconstructed states, not stored text.

This shift from content-centric to state-centric representation makes versioning structural rather than cosmetic.

---

## Core Concepts

### Truth State

A **truth state** is the complete, internally consistent set of all facts known to the system at a given version tag.

Formally: given an initial state S₀ and an ordered sequence of deltas [δ₁, δ₂, ..., δₙ], the truth state at version vₖ is the result of applying all deltas with version tag ≤ vₖ to S₀.

### Delta

A **delta** is the smallest unit of knowledge modification recognized by the system.

Each delta:

- **Identifies** the specific knowledge atom it affects
- **Declares** the transformation it performs (addition, modification, or retraction)
- **Records** the causal trigger that produced it (e.g., a document update, a correction)
- **Carries** a version tag that positions it in the ordered sequence

A delta does not contain the full text of its source document. It contains the logical effect of that document on the system's knowledge.

### Version Tag

A **version tag** is a monotonically ordered label that positions a delta in the causal sequence.

Tags follow a predictable, comparable scheme. The exact scheme is implementation-defined, but all implementations must guarantee: given two tags tₐ and t_b, it is always possible to determine which represents the later state.

### Trajectory

A **trajectory** is the ordered sequence of all deltas from an initial truth state to a target truth state.

It encodes the full causal history of knowledge evolution between two points, answering: "What happened, in what order, to reach this state?"

### State Reconstruction

**State reconstruction** is the deterministic process of applying an ordered set of deltas to an initial state.

Given identical inputs (initial state + deltas), reconstruction always produces identical outputs. This property enables auditability: any truth state can be re-derived and verified.

### Knowledge Atom

A **knowledge atom** is the persistent identity to which deltas apply.

When a delta modifies a fact, it does not create a new, unrelated entity. It transforms an existing atom from one value to another while preserving identity. This identity persistence is what enables trajectory tracking across versions.

Example atoms: "data retention period," "maximum connection timeout," "authorized signatory list."

### Semantic Memory

**Semantic memory** is the set of all facts in a given truth state, divorced from the history of how they arrived.

A query for "current truth" retrieves from semantic memory—the net result of all deltas, without provenance.

### Episodic Memory

**Episodic memory** is the full trajectory of deltas leading to a truth state.

A query for "how this changed" retrieves from episodic memory—the sequence of transformations, with their causes and timestamps.

### Current Truth

The **current truth** is the truth state at the highest version tag in the system.

### Historical Truth

A **historical truth** is any truth state at a version tag earlier than the current one.

The system can reconstruct any historical truth deterministically by applying only the deltas up to the requested tag.

---

## High-Level Architecture

The Veridia pipeline consists of five stages. Each stage has clearly defined inputs and outputs.

### 1. Ingestion

**Input:** A document (policy, specification, finding, update notice) plus metadata (source, timestamp, version identifier from the source system).

**Output:** The document content, normalized for processing.

### 2. Transformation

**Input:** Normalized document content plus the current truth state.

**Output:** One or more deltas.

This stage is where the document is converted into causal units. An LLM or deterministic parser analyzes the document against the current state and produces deltas that express:

- Which knowledge atoms are affected
- What the new values are
- What the previous values were
- The causal event that triggered the change

The source document is not stored beyond transformation.

### 3. Storage

**Input:** Ordered deltas with version tags.

**Output:** An append-only delta log.

Deltas are immutable once stored. The version tag determines insertion order. The log serves as the system's source of truth; all states are reconstructed from this log.

### 4. Retrieval

**Input:** A query specifying what information is needed and (optionally) at what version.

**Output:** A set of deltas or a reconstructed truth state.

The LLM interprets the query to determine:

- The target version tag (explicit or inferred as current)
- Whether the query requires semantic memory (state) or episodic memory (trajectory)

The retrieval mechanism then either:

- Reconstructs the truth state at the target version and returns the relevant facts, or
- Returns the ordered deltas in the trajectory leading to the target version

No similarity search is performed at retrieval time.

### 5. Response Generation

**Input:** The retrieved state or trajectory plus the original user query.

**Output:** A natural language response.

The LLM synthesizes a response from the retrieved information. For multi-version queries, it may compare states side by side, explain when and why changes occurred, or present the evolution of a fact over time.

---

## Simple Example

### Documents Ingested

**Policy v1.0** (ingested 2025-01-15):
> Data retention period: 90 days.

**Policy v2.0** (ingested 2025-06-01):
> Data retention period: 30 days, per compliance review.

### Generated Deltas

**Delta 1** (tag: `v1.0`):
- Atom: `data_retention_period`
- Action: set value to `90 days`
- Cause: initial policy publication

**Delta 2** (tag: `v2.0`):
- Atom: `data_retention_period`
- Action: change value from `90 days` to `30 days`
- Cause: compliance review

### Query

> "What was the data retention period on May 1, 2025?"

### Retrieval

Target version: `v1.0` (latest tag ≤ May 1, 2025).  
Reconstruct state up to Delta 1.  
Retrieve atom `data_retention_period` → value is `90 days`.

### Response

> "On May 1, 2025, the data retention period was 90 days. This was the initial policy, published January 15, 2025. On June 1, 2025, a compliance review changed the period to 30 days."

---

## Architectural Principles

1. **Determinism.** Given the same inputs, state reconstruction always produces the same output. There is no randomness, ranking, or probabilistic retrieval.

2. **Immutability.** Once stored, a delta is never modified. Corrections arrive as new deltas that supersede prior ones while preserving the historical record.

3. **Causality.** Every state transition records its trigger. The system can answer not just "what changed?" but "why?"

4. **Temporal ordering.** Version tags provide a total order. For any two deltas, the system can determine which preceded the other.

5. **Identity persistence.** Knowledge atoms maintain identity across versions. A changed fact is the same fact, not a new fact.

Full architecture documentation is available in [docs/architecture.md](docs/architecture.md).

---

## Advantages

Veridia's design is appropriate under the following conditions:

- **The evolution of knowledge matters.** If knowing what was true at a specific time is critical—compliance, legal reasoning, policy enforcement—Veridia provides temporal guarantees that similarity-based retrieval cannot.

- **Auditability is required.** Because state reconstruction is deterministic and deltas are immutable, every response can be traced to the exact deltas that produced it.

- **Documents are structured updates.** When new documents frequently amend, supersede, or retract prior documents, the delta model captures this directly.

- **Operational simplicity is valued.** Veridia eliminates the operational burden of vector databases, embedding pipelines, and similarity index maintenance.

---

## Limitations

Veridia is not appropriate for all retrieval use cases.

### Where Veridia performs poorly

- **Static knowledge bases.** If the knowledge never changes, the versioning and causal tracking infrastructure provides no benefit over document storage.

- **Open-ended semantic search.** Veridia does not support "find documents similar to this idea" queries. It retrieves by known atoms and states, not by topical proximity.

- **Unstructured text with no clear atoms.** If documents do not contain extractable, identifiable facts with persistent identity, delta extraction becomes unreliable.

### Comparison with other architectures

| Architecture | Strength | Weakness in evolving knowledge |
|---|---|---|
| **Traditional RAG** | Broad semantic coverage; low ingestion cost | Versions mix; no temporal guarantees |
| **Hybrid RAG (metadata-filtered)** | Temporal filtering reduces version mixing | Filtering is heuristic; no causal tracking |
| **Knowledge Graphs** | Structured facts; explicit relations | Versioning requires graph versioning infrastructure; temporal queries complex |
| **Veridia** | Temporal consistency; causal traceability; deterministic reconstruction | Requires atom-identifiable knowledge; higher ingestion cost; unsuited for pure semantic search |

This comparison describes architectural tradeoffs, not empirical performance. Benchmarks measuring these tradeoffs are under development.

---

## Benchmarks

Veridia defines benchmark metrics aligned with its architectural goals:

### Metrics

| Metric | Definition |
|---|---|
| **Temporal Precision** | Proportion of retrieved facts that were actually true at the queried version tag |
| **Trajectory Completeness** | Proportion of state transitions in the ground truth that are represented in the delta log |
| **Reconstruction Determinism** | Binary verification that reconstruction from the delta log produces identical states across runs |
| **Provenance Accuracy** | Proportion of retrieved facts with correct causal attribution |

### Status

Benchmark datasets, ground truth generation methods, and evaluation harnesses are in development. Results will be published in the [benchmarks/](benchmarks/) directory.

**No benchmark results are available at this time.**

---
