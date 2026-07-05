# Veridia

## Veridical Diachronic System

Veridia is a knowledge-storage architecture built around **versioned, atomic causal events** — **deltas** — instead of embeddings and vector similarity. It is designed for domains where facts change constantly and **when something was true matters as much as what is true now**.

---

# 1. The Problem

Most retrieval systems treat knowledge as a static snapshot. In practice, knowledge is **diachronic** — it changes over time, and old versions still matter for context, audit, and causal reasoning.

Two failure modes show up repeatedly in production:

- **Temporal inconsistency:** when a source document is updated, there is no reliable, built-in mechanism to know which version is currently true versus what used to be true.

- **Lost causality:** systems can retrieve content that is topically similar to a query, but they cannot answer **why** something happened or **what it leads to** — because similarity and causation are not the same thing.

---

# 2. Why Current Solutions Fall Short

| **Approach** | **Core limitation** |
|--------------|---------------------|
| **RAG (embeddings + vector DB)** | Similarity ≠ causality. Retrieves what sounds relevant, not what causally connects. No native versioning — updates require re-embedding and re-indexing. |
| **Knowledge Graphs** | Causal structure exists, but building and maintaining it at scale requires heavy manual curation or brittle NLP pipelines. Ontology drift becomes a maintenance burden. |
| **Approach** | **Core limitation** |
|--------------|---------------------|
| **Event Sourcing** | Captures what happened, but treats events as opaque — no native causal linking or LLM-level interpretation between events. |
| **CQRS + Event Store** | Solves consistency at the infrastructure level, but adds significant architectural overhead (separate read/write models, replay logic) with no semantic reasoning layer. |
| **Temporal Databases** | Solve **when** something was true extremely well, but have no concept of causal relationship between records — they are timestamped tables, not causal chains. |
| **Hybrid Retrieval** | Combines several of the above to patch individual weaknesses, but multiplies operational complexity, latency, and infrastructure cost rather than resolving the underlying gap. |

In short: causal reasoning, temporal consistency, and low-cost updates are each solved partially, by different systems — **never together, in one lightweight architecture.**

---

# 3. Why Veridia

Veridia treats **causality** and **time** as first-class citizens, not as afterthoughts bolted onto a similarity search engine.

- Every unit of knowledge is a **discrete, versioned causal event**.
- The **current truth** is always a deterministic lookup, not a race between an update and a reindex job.
- History is never discarded — it's preserved for audit and reconstruction of past states.
- An LLM is used as an **interpretation layer**, not as a storage mechanism — intelligence lives in reading, not in the index.

---

# 4. The Approach: Deltas
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
```

### Key properties

- **No embeddings, no vector database.** Retrieval is a direct lookup by causal key (hash index / B-tree), not approximate nearest-neighbor search.

- **No dedicated GPU infrastructure required** for storage or retrieval — the only inference cost is the LLM call itself (extraction, verification, interpretation), which can run entirely against a hosted API.

- **Updates are near O(1):** replacing a fact means writing one new delta, not re-embedding or reindexing anything.

- **Extraction runs on a two-pass pipeline:**
  1. Extraction against a causal checklist.
  2. Verification with mandatory grounding against the source text, ideally using a different model than the extractor to reduce correlated error.

- Documents are processed in **medium-sized windows (~2000–5000 tokens)**, large enough to preserve intra-document causal relationships without triggering **"lost in the middle"** degradation.

---

# 5. Complexity & Latency — Architectural Comparison

The table below reflects **architectural complexity classes** and known structural properties of each paradigm — **not published empirical benchmark numbers**.

**Empirical validation is pending (see Known Limitations).**

| **System** | **Update cost** | **Query cost** | **Native causal reasoning** | **Native temporal consistency** | **Requires vector infra / GPU** |
|-------------|----------------:|---------------:|:---------------------------:|:-------------------------------:|:-------------------------------:|
| **RAG (vector DB)** | O(chunk) re-embed + reindex | O(log n) approx. search | ❌ No | ❌ No | ✅ Yes |
| **Knowledge Graph** | O(edges affected) + curation | O(graph traversal) | ✅ Yes | ❌ No | ❌ No *(but curation-heavy)* |
| **Event Sourcing** | O(1) append | O(n) replay or O(1) w/ snapshot | ❌ No | ◐ Partial *(append-only)* | ❌ No |
| **CQRS + Event Store** | O(1) append, async projection | O(1) on read model | ❌ No | ◐ Partial | ❌ No |
| **Temporal Database** | O(1) insert w/ timestamp | O(log n) range query | ❌ No | ✅ Yes | ❌ No |
| **Hybrid Retrieval** | Sum of components | Sum of components | ◐ Partial | ◐ Partial | ✅ Usually yes |
| **Veridia** | **~O(1) per delta** | **O(1) / O(log n) by causal key** | **✅ Yes (native)** | **✅ Yes (native, versioned)** | **❌ No** |

---

# 6. What Sets Veridia Apart

- **Causality is structural, not inferred** — relationships are stored explicitly, not approximated through embedding proximity.

- **"Current truth" is a deterministic query**, eliminating the inconsistency window inherent to reindex-based systems.

- **Full audit trail by default** — every past state is reconstructable, with no extra engineering.

- **Update cost stays flat regardless of corpus size**, because updates touch one delta, not a document or an index shard.

- **Zero embedding/vector infrastructure dependency** — lower operational cost and simpler deployment footprint.

# 7. Known Limitations

Although Veridia addresses several structural limitations of current retrieval architectures, it is not without trade-offs.

- **Extraction reliability is bounded by the underlying LLM.** Grounding reduces hallucination significantly but does not eliminate it entirely.

- **Verifier correlation risk:** if the verifier shares architecture/training with the extractor, errors can still correlate even with a two-pass design.

- **Reconciliation across deltas is not naturally O(n²)-safe** — contradiction detection between deltas requires pre-filtering (by causal key / domain) to stay tractable at scale.

- **Weak on vague, paraphrased, or purely semantic queries** — without an explicit causal key match, Veridia does not generalize as gracefully as embedding-based similarity search.

- **Storage grows with revision history, not just corpus size** — requires a cold-archiving strategy for long-lived deployments.

- **Cross-delta temporal dependencies** (delta B depends on delta A's state at a specific point in time) introduce distributed-systems-like resolution complexity that a single timestamp field does not fully solve.

- **No published empirical benchmarks yet** — the comparison table above is architectural/theoretical; real latency and accuracy numbers require running the golden-set evaluation methodology against production-scale data.