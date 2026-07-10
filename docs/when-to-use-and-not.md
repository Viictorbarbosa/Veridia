 # When to Use Veridia

Veridia is **not** a universal replacement for RAG. It excels under a specific set of conditions and performs worse under others.

This document exists to make that decision explicit rather than leaving it to intuition.

---

# 1. Quick Decision Guide

| Your situation | Recommendation |
|---------------|----------------|
| Source documents change frequently, and **"what's true now"** matters | **Veridia** |
| You need to reconstruct **"what we knew at time X"** (audit, compliance, post-mortem) | **Veridia** |
| Domain has clear, nameable causal relationships (**A leads to B**) | **Veridia** |
| Queries are broad, exploratory, or loosely worded | **RAG** |
| Corpus is large, open-domain, and topically diverse | **RAG** |
| Corpus is fairly static but query volume is very high | **RAG**, or **Veridia** with aggressive interpretation caching |
| Both structured causal facts and open-ended exploration are needed | **Hybrid** (see §3) |
| You don't have the resources to build and maintain a grounding + verification pipeline | **RAG** — Veridia's reliability guarantees only hold if the pipeline is actually maintained |

# 2. Use Veridia When

Use Veridia when one or more of the following conditions apply:

- **Documents mutate constantly**, and stale answers are costly (e.g., policy, regulation, operational runbooks, pricing rules, technical configuration state).

- **Causal precision matters more than topical recall** — the question is *"Why did X happen?"* or *"What does Y lead to?"*, not *"Find me something related to Y."*

- **An audit trail is a requirement**, not a nice-to-have — for regulated industries, legal, financial, or any domain where **what was true when a decision was made** must be reconstructable.

- **Update cost is the bottleneck**, not raw query latency — for example, a knowledge base with hundreds of small edits per week, where re-embedding and re-indexing every change becomes operationally expensive.

- **The domain has natural causal keys** — entities, error codes, policy clauses, configuration parameters, or similar concepts that queries can resolve against directly without relying on fuzzy semantic matching.

- **You want to avoid running vector database infrastructure entirely.**

# 3. Use RAG (or a Hybrid) When

Use RAG—or combine it with Veridia—when one or more of the following conditions apply:

- **The corpus is open-domain or exploratory** — general documentation, broad knowledge bases, or content where users ask loosely worded or heavily paraphrased questions.

- **Semantic fuzziness is the norm**, not the exception. Without an explicit causal-key match, Veridia does not generalize as gracefully as embedding-based similarity.

- **Query volume is very high** while the corpus changes relatively rarely. RAG front-loads its cost (embed once, query cheaply), whereas Veridia performs an interpretation step for each query unless the result is cached. In this scenario, RAG may be more cost-effective.

- **You cannot commit to maintaining the extraction pipeline.** Grounding, a dedicated verification model, a golden set, and periodic reconciliation are the mechanisms that make Veridia's consistency guarantees meaningful. Without them, Veridia effectively becomes a more complex and less efficient version of RAG.

The practical default for mixed requirements is a **hybrid architecture**:

- Use **Veridia** to model the core domain with explicit causal relationships.
- Use **RAG** as a fallback for queries that fall outside the modeled causal graph.

This architecture is typically the most defensible production approach, since neither a pure Veridia system nor a pure RAG system handles both structured causal reasoning and open-ended exploration equally well.

# 4. Cost Framing *(Not a Benchmark — a Model)*

| Aspect | RAG | Veridia |
|--------|-----|----------|
| **Upfront cost** | Low (batch embeddings) | Higher (extraction + grounding + verification pipeline) |
| **Cost per document update** | Medium–high (re-embed + re-index) | Low (~O(1) — write one delta) |
| **Cost per query** | Low (vector search) | Medium–high, unless interpretation is cached |
| **Where cost accumulates** | Over time, as updates pile up | Upfront, and per query if uncached |

> **Break-even depends almost entirely on update frequency.**

High-churn content quickly shifts the cost advantage toward **Veridia**.

Low-churn, high-query-volume content generally favors **RAG**, unless Veridia includes an effective interpretation caching strategy.

# 5. Choosing MVP vs. Scalable Tier

Start with the **MVP tier**, regardless of your long-term target use case.

It is the fastest way to prove—using your own **golden-set metrics**—that Veridia's delta consistency outperforms your current RAG solution before investing in additional routing infrastructure.

Move to the **Scalable tier** only when one or more of the following conditions become true:

- Multiple distinct domains or specialties compete for the same index.
- Delta volume has grown enough that a single monolithic lookup measurably reduces retrieval precision.

Keep in mind that **routing introduces a new failure mode: misclassification**.

Only adopt routing once there is clear evidence that its benefits outweigh the additional complexity. Until then, a simpler architecture is generally easier to validate, operate, and maintain.

# 6. Red Flags — Signs Veridia Is the Wrong Tool

Veridia is probably **not** the right solution if one or more of the following conditions apply:

- Your queries are primarily **"find me something like X"** and there is **no stable causal key** to anchor retrieval.

- Your content **rarely changes**, and your primary cost driver is **query volume**, not update frequency.

- You cannot commit engineering time to maintaining:
  - Grounding
  - A golden set
  - Periodic reconciliation

  Without these components, Veridia's core reliability claim does not hold.

- Your domain does **not** have clear, nameable **cause → effect** relationships (e.g., general creative content, broad Q&A, or marketing copy).