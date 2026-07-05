# Veridia
### *Veridical Diachronic System*

Veridia is a knowledge-storage architecture built around **versioned, atomic causal events** — *deltas* — instead of embeddings and vector similarity. It is designed for domains where facts change constantly and *when something was true* matters as much as *what is true now*.

---

## 1. The Problem

Most retrieval systems treat knowledge as a static snapshot. In practice, knowledge is *diachronic* — it changes over time, and old versions still matter for context, audit, and causal reasoning.

Two failure modes show up repeatedly in production:

- **Temporal inconsistency**: when a source document is updated, there is no reliable, built-in mechanism to know *which version is currently true* versus *what used to be true*.
- **Lost causality**: systems can retrieve content that is *topically similar* to a query, but they cannot answer *why something happened* or *what it leads to* — because similarity and causation are not the same thing.

---

## 2. Why Current Solutions Fall Short

| Approach | Core limitation |
|---|---|
| **RAG (embeddings + vector DB)** | Similarity ≠ causality. Retrieves what *sounds* relevant, not what *causally* connects. No native versioning — updates require re-embedding and re-indexing. |
| **Knowledge Graphs** | Causal structure exists, but building and maintaining it at scale requires heavy manual curation or brittle NLP pipelines. Ontology drift becomes a maintenance burden. |
| **Event Sourcing** | Captures *what happened*, but treats events as opaque — no native causal linking or LLM-level interpretation between events. |
| **CQRS + Event Store** | Solves consistency at the *infrastructure* level, but adds significant architectural overhead (separate read/write models, replay logic) with no semantic reasoning layer. |
| **Temporal Databases** | Solve *when* something was true extremely well, but have no concept of *causal relationship* between records — they are timestamped tables, not causal chains. |
| **Hybrid Retrieval** | Combines several of the above to patch individual weaknesses, but multiplies operational complexity, latency, and infrastructure cost rather than resolving the underlying gap. |

*In short: causal reasoning, temporal consistency, and low-cost updates are each solved partially, by different systems — never together, in one lightweight architecture.*

---

## 3. Why Veridia

Veridia treats **causality and time as first-class citizens**, not as afterthoughts bolted onto a similarity search engine.

- Every unit of knowledge is a discrete, **versioned causal event**.
- The *current truth* is always a deterministic lookup, not a race between an update and a reindex job.
- History is never discarded — it's preserved for audit and reconstruction of past states.
- An LLM is used as an **interpretation layer**, not as a storage mechanism — intelligence lives in *reading*, not in the index.

---

## 4. The Approach: Deltas

Instead of chunking documents arbitrarily, Veridia decomposes documents into **deltas** — atomic causal units, each independently addressable, versioned, and updatable.

```json
{
  "id": "uuid",
  "causal_key": "auth.token_expiry",
  "content": "Session timeout triggers automatic logout",
  "cause": "delta_id | null",
  "effect": ["delta_id", "..."],
  "timestamp": "ISO8601",
  "previous_version": "delta_id | null",
  "active": true
}