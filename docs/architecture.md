# Veridia Architecture

> **For the problem statement and comparative rationale, see `README.md`.**  
> **For guidance on when to use Veridia vs. alternatives, see `when-to-use.md`.**

This document describes the internal architecture of Veridia:

- Delta model
- Versioning mechanics
- Extraction pipeline
- Two implementation tiers (MVP and Scalable)

---

# 1. Core Concept: Deltas

A **delta** is the atomic unit of stored knowledge—one causal event or fact, independently addressable, versioned, and updatable in isolation.

Instead of splitting documents into arbitrary fixed-size chunks, Veridia decomposes them into **semantic deltas**.

## Delta Schema

```json
{
  "id": "uuid",
  "causal_key": "auth.token_expiry",
  "content": "Session timeout triggers automatic logout",
  "cause": "delta_id | null",
  "effect": [
    "delta_id",
    "..."
  ],
  "timestamp": "ISO8601",
  "previous_version": "delta_id | null",
  "active": true
}
```

## Field Definitions

| Field | Purpose |
|--------|----------|
| `causal_key` | Stable identifier for the fact/entity this delta describes. Primary lookup key. |
| `cause` / `effect` | Explicit links to other deltas, forming a causal chain instead of relying on inferred similarity. |
| `timestamp` | When this version became true. Basis for temporal queries. |
| `previous_version` | Pointer to the delta this one supersedes, forming the version chain. |
| `active` | `true` for the current truth, `false` once superseded. Never deleted. |

Deltas are intentionally cheap to update.

Replacing a fact only requires:

1. Writing one new delta.
2. Marking the previous delta as inactive.

No re-embedding, re-indexing, or modification of unrelated records is required.

---

# 2. Versioning & Temporal Truth

Every delta is versioned using a timestamp, producing two independent query layers.

## Current Truth

The active delta for a given `causal_key`.

Lookup is deterministic:

```sql
WHERE causal_key = ?
AND active = true
```

This avoids races against background re-indexing jobs.

---

## History

Every previous version is preserved indefinitely.

This enables reconstruction of:

- historical knowledge,
- previous system state,
- audit trails,
- temporal reasoning.

---

When a fact changes, Veridia **never overwrites data**.

Instead it:

1. creates a new delta;
2. links it to the previous version;
3. marks the previous delta as inactive.

Conflicts therefore become explicit first-class events rather than silently coexisting vectors inside an embedding space.

---

## Known Complexity

Cross-temporal dependencies introduce additional complexity.

For example:

- Delta **B** may depend on the state of delta **A** at the time B was created.
- Later, **A** changes.

A single timestamp is not always sufficient to resolve consistency.

This resembles ordering problems in distributed systems (similar to **vector clocks**) and should be addressed explicitly for each domain rather than assumed solved by timestamps alone.

---

## Storage Trade-off

History grows proportionally to:

```
O(corpus × revisions over time)
```

rather than:

```
O(corpus)
```

This is intentional.

Historical deltas represent an audit trail rather than storage waste.

For long-lived deployments, inactive deltas should eventually be moved to cold storage after a defined retention period.

# 3. Extraction Pipeline

Deltas are produced through a **two-pass LLM pipeline** operating on medium-sized document windows (~2,000–5,000 tokens).

This window size is intentionally chosen to:

- Preserve intra-document causal relationships.
- Avoid the "lost in the middle" degradation observed with very large contexts.

```text
Document
    │
    ▼
Pass 1: Extraction
    │
    ▼
Pass 2: Verification
    │
    ▼
Deltas
```

---

## Pass 1 — Extraction

The extraction model does **not** freely decide what information is worth storing.

Instead, it follows:

- A predefined checklist of delta types.
- A fixed logical extraction order.

This approach:

- reduces run-to-run variance;
- improves consistency;
- forces systematic document coverage.

---

## Pass 2 — Verification

The verification stage ensures that:

- every checklist item was processed;
- extracted relationships are supported by the document;
- hallucinated causal links are rejected.

The objective is to maximize extraction reliability before any delta reaches storage.

---

# 3.1 Reliability Refinements

| Refinement | What it solves |
|------------|----------------|
| **Mandatory grounding** | Every delta must reference the exact source span from which it was extracted. If the verifier cannot locate that span in the document, the delta is automatically rejected. This converts "Does the LLM think this is correct?" into a near-deterministic structural validation and provides a measurable quality metric (grounding rejection rate ≈ hallucination proxy). |
| **Verifier on a different model than the extractor** | Using the same model for generation and verification correlates their errors. A hallucination is therefore more likely to be accepted. Using a different model (with comparable capability but different lineage) reduces this correlation. This doubles extraction-time inference cost, but only once per document—not per query. |
| **Golden set** | Maintain a dataset of 20–30 manually annotated documents, stratified by difficulty (clear causal links, ambiguous cases, multi-paragraph relationships, etc.). Execute this benchmark during CI whenever prompts change, allowing precision and recall changes to be measured instead of assumed. |
| **Periodic reconciliation** | Execute a periodic process (not per document) that searches for contradictions among existing deltas. A naïve all-pairs comparison would be **O(n²)** and therefore impractical. Candidate pairs should first be filtered by `causal_key`, domain, or project before applying LLM reasoning to the reduced search space. |

---

## Residual Limitation

Reconciliation still depends on LLM judgment.

Unlike mandatory grounding, contradiction detection is **not deterministic**.

Its purpose is to reduce the error surface—not eliminate it completely.

---

## Suggested Build Order

Implement reliability layers in the following order:

1. **Mandatory grounding**
2. **Golden set**
3. **Verifier using a different model**
4. **Periodic reconciliation**

This order establishes measurable quality first, improves precision second, and introduces contradiction detection only when the volume of stored deltas becomes large enough for it to provide meaningful value.

# 4. Query Flow

The retrieval process in Veridia is deterministic and centered around **causal keys**, rather than semantic similarity.

```text
User Question
      │
      ▼
Lookup by causal_key (Index)
      │
      ▼
Active Delta(s)
      │
      ▼
LLM Interpretation Layer
      │
      ▼
Answer
```

---

## Retrieval

Retrieval is performed through a direct index lookup.

Unlike traditional RAG systems, Veridia does **not** require:

- Query embedding generation
- Approximate Nearest Neighbor (ANN) search
- Similarity ranking across document chunks

Instead, the system retrieves the relevant **active delta(s)** directly from storage.

---

## LLM Responsibilities

The LLM is **not responsible for search**.

Its role is limited to interpreting and combining retrieved deltas.

Typical responsibilities include:

- Connecting causal relationships.
- Following multi-step cause–effect chains.
- Producing natural-language explanations.
- Generalizing across retrieved facts.

Knowledge storage and retrieval remain deterministic.

---

For a complete visualization of the architecture, including causal chains and versioning examples, see:

```text
docs/diagrams/veridia-flow.svg
```

---

# 5. Implementation Tiers

Veridia is designed to evolve through two implementation stages.

---

# 5.1 MVP

## Goal

Validate that delta-based storage outperforms conventional RAG in:

- consistency;
- update cost;
- deterministic retrieval.

while keeping engineering complexity as low as possible.

---

## Storage

A single PostgreSQL instance.

Current-truth retrieval is supported by a unique index on:

```sql
(causal_key, active = true)
```

This provides approximately:

- **O(1)** lookup (hash index)
- **O(log n)** lookup (B-tree)

depending on the indexing strategy.

---

## Pipeline

The MVP intentionally minimizes architectural complexity.

Characteristics:

- One LLM performs extraction.
- The same LLM performs query-time interpretation.
- No caching layer.
- No domain routing.
- Single storage backend.

---

## Success Criteria

The MVP is considered successful if it demonstrates that:

- causal queries remain correct after repeated document updates;
- updating knowledge costs significantly less than re-indexing an equivalent RAG pipeline;
- deterministic retrieval remains stable as documents evolve.

# 5.2 Scalable (Session-Based Routing)

## Goal

Prevent a single monolithic index from becoming slow, inefficient, or ambiguous as the number of stored deltas grows across multiple domains.

Instead of storing every delta in one global repository, Veridia partitions knowledge into **sessions**.

---

## Session

A **session** is a logical grouping of deltas belonging to the same domain.

Examples include:

- Legal
- Operations
- Product
- Finance
- Security

Each session may have:

- its own index;
- its own storage partition;
- its own prompt;
- its own specialized LLM.

Example:

```json
{
  "...base_delta": "...",
  "session_id": "string",
  "specialty": "string",
  "relevance_weight": "float"
}
```

---

## Routing Layer

Before retrieval begins, a lightweight classifier determines which session is most relevant to the user's query.

```text
User Question
      │
      ▼
Session Router
      │
      ▼
Selected Session
      │
      ▼
Lookup by causal_key
      │
      ▼
Retrieved Delta(s)
      │
      ▼
LLM Interpretation
```

Instead of searching the entire corpus, Veridia narrows the search space by selecting the most relevant session first.

This improves scalability while reducing unnecessary lookups.

---

## Storage Strategy

Each session behaves as an independent shard.

Possible implementations include:

- Separate PostgreSQL tables.
- Table partitioning.
- Independent databases.
- Distributed storage nodes.

Because sessions are isolated, they can scale independently without affecting unrelated domains.

---

## Critical Trade-off

Routing accuracy becomes one of the most important components of the architecture.

If the router assigns a query to the wrong session, retrieval never reaches the correct deltas, regardless of how effective the retrieval process is within that session.

Consequently, routing precision becomes a primary scalability bottleneck.

---

## Low-Confidence Fallback

To mitigate routing errors, Veridia should include a fallback mechanism.

When routing confidence is below a predefined threshold, the system performs a broader search across multiple sessions instead of relying exclusively on the initial routing decision.

This fallback is **not optional** for production deployments, as it preserves recall when classification uncertainty is high.

# 6. Future Work: Meta-Deltas

Once Veridia has accumulated knowledge across enough projects and domains, a new abstraction layer becomes possible: **meta-deltas**.

Rather than representing individual facts, meta-deltas capture **patterns discovered across many deltas**.

Example:

```json
{
  "type": "meta_delta",
  "pattern": "Verifier sharing the extractor's model",
  "occurrences": 4,
  "consistent_outcome": "High false-negative rate in ambiguous domains",
  "related_projects": [
    "project_a",
    "project_c",
    "project_f"
  ]
}
```

---

## Purpose

Meta-deltas transform accumulated project history into reusable, evidence-backed heuristics.

Instead of relying on generic best practices, Veridia can learn from recurring patterns observed across multiple projects and domains.

Examples include:

- recurring architectural failures;
- successful implementation strategies;
- common extraction errors;
- prompt engineering patterns;
- model-specific behaviors;
- recurring causal structures.

Over time, this enables the system to improve future decision-making using knowledge derived from prior experience.

---

## Risk: Overfitting

A significant risk is **overfitting to historical experience**.

Patterns that were consistently valid in the past may become obsolete as:

- LLM capabilities evolve;
- prompting techniques improve;
- extraction pipelines change;
- retrieval strategies mature.

Therefore, a meta-delta should not be considered permanently valid.

---

## Revalidation

Each meta-delta should include an expiration or revalidation policy.

Instead of storing only a creation date, it should also define when the pattern must be evaluated again against newer models, updated datasets, or revised extraction pipelines.

This ensures that accumulated heuristics remain evidence-based rather than becoming outdated assumptions.

# 7. Technical Risk Summary

Veridia intentionally separates its challenges into two categories:

- **Hard problems**, which are closer to applied research.
- **Manageable engineering problems**, which can be addressed using well-established software engineering practices.

---

## Hard Core

These are the primary research risks of the architecture.

### Reliable Causal Extraction via LLM

The quality of the entire system depends on consistently extracting causal relationships from documents.

Although grounding, verification, and benchmarking significantly improve reliability, perfect extraction remains an open research problem.

---

### Resolving Cross-Temporal Delta Dependencies

Versioning individual deltas is straightforward.

However, maintaining consistency when multiple deltas depend on historical states of one another introduces challenges similar to those found in distributed systems.

This problem becomes increasingly complex as knowledge evolves over time.

---

### Routing Precision at Production Scale

In the Scalable architecture, routing accuracy becomes critical.

If a query is classified into the wrong session, retrieval cannot reach the correct deltas, regardless of how efficient the retrieval algorithm itself may be.

Consequently, routing quality becomes one of the main determinants of system performance at scale.

---

## Manageable Complexity

The following components rely on mature engineering practices rather than unsolved research.

- PostgreSQL storage infrastructure and indexing.
- Extensible schema evolution using optional fields without breaking backward compatibility.
- Integration with LLM APIs.

Although these components require careful implementation, they are well understood and supported by existing technologies.

---

## Final Assessment

The fundamental question is **not** whether Veridia can function as a prototype—it can.

The real challenge is whether the architecture maintains its consistency under real-world conditions, where documents change continuously and unpredictably.

Each reliability layer contributes to this goal:

- Grounding
- Dual-model verification
- Golden-set evaluation
- Periodic reconciliation

However, each layer also increases implementation complexity and inference cost.

For this reason, development should proceed incrementally:

1. Build and validate the **MVP**.
2. Measure reliability and update performance.
3. Introduce scalability features only after the MVP demonstrates consistent behavior under real document churn.

This staged approach minimizes engineering risk while allowing the architecture to evolve based on empirical evidence rather than assumptions.