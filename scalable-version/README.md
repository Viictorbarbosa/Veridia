# *Veridia — Scalable Tier*


This tier adds **session-based routing** on top of the MVP's flat index. It exists for one reason: a single monolithic causal-key lookup becomes slower and more ambiguous as multiple unrelated domains (legal, ops, product, support, etc.) accumulate deltas in the same store.

> **Don't start here.** Build the MVP first, validate the consistency improvements with your own golden set, and only adopt this tier once you've actually reached the bottleneck it solves (see `when-to-use.md`, §5).

---

# *1. What's Included*

| File | Purpose |
|------|---------|
| `schema.sql` | Extends the MVP delta schema with `session_id`, `specialty`, and `relevance_weight`, plus session-scoped indexes. The migration is additive and remains compatible with existing MVP data. |
| `router.py` | Classifies incoming questions into a session (domain) before lookup, producing a confidence score and falling back to cross-session search when confidence is low. |
| `confidence_test.py` | Evaluates router accuracy using a labeled set of *(question, expected_session)* pairs before production deployment. |

---

# *2. Requirements*

This tier has the same requirements as the MVP:

- *Python 3.10+*
- *A PostgreSQL instance*
- *An LLM API key*

No additional infrastructure is required—this tier introduces a structural change, not a new service.

---

# *3. Setup*

## *1. Migrating from the MVP*

If you're upgrading from the MVP, existing deltas won't contain a `session_id`.

The migration is handled automatically by `schema.sql`, which safely:

- adds the `session_id` column using `IF NOT EXISTS`;
- backfills existing rows into the `default` session using an `UPDATE` statement.

No manual SQL is required.

---

## *2. Apply the schema*

```bash
psql "$DATABASE_URL" -f schema.sql
```

---

## *3. Define your sessions*

A session consists of:

- a `session_id`;
- a short natural-language specialty description used by the router.

Example:

| Session | Specialty |
|---------|-----------|
| `legal` | *contract terms, compliance clauses, regulatory obligations* |

This configuration can live in a JSON file, a database table, or wherever your router configuration is maintained.

---

## *4. Validate the router*

```bash
python confidence_test.py
```

Don't enable session-scoped lookup in production until the router reaches a confidence threshold you're comfortable with (see §5).

---

# *4. How It Works*

```text
Question
   │
   ▼
router.py: classify session
        │
        ├── High confidence ─────► Session lookup
        │                              │
        │                              ▼
        │                      Interpretation
        │                              │
        │                              ▼
        │                           Answer
        │
        └── Low confidence ──────► Cross-session lookup
                                       │
                                       ▼
                               Interpretation
                                       │
                                       ▼
                                    Answer
```

The router executes **before** any causal-key resolution.

It first narrows the search space, after which the standard MVP key-resolution pipeline (`mvp/query.py`) runs unchanged, but restricted to the selected session.

Queries with low confidence **must never** search only the highest-scoring session. Instead, they fall back to a cross-session search.

A wrong-session lookup is worse than a slightly slower cross-session search because it prevents the query from ever reaching the correct deltas.

---

# *5. The Confidence Test*

`confidence_test.py` reports three primary metrics.

| Metric | Description |
|--------|-------------|
| **Routing accuracy** | Percentage of questions classified into the correct session. |
| **Confidence calibration** | Measures whether higher confidence actually correlates with correct classifications. A router that is confidently wrong is more dangerous than one that triggers fallback. |
| **Fallback rate** | Percentage of queries that trigger cross-session lookup due to low confidence. Increasing fallback rates usually indicate overlapping session definitions. |

Re-run this test whenever sessions are added, removed, or redefined.

Routing accuracy depends not only on the router implementation but also on how well your session boundaries are defined.

---

# *6. Success Criteria*

- [ ] Routing accuracy on the labeled dataset remains above your chosen threshold (a conservative starting point is **90%+**).
- [ ] Low-confidence queries consistently fall back to cross-session search instead of returning incorrect session results.
- [ ] Query latency remains acceptable compared to the MVP's flat lookup.
- [ ] Adding or modifying sessions does not silently reduce accuracy on existing sessions (re-run `confidence_test.py` after every session change).

---

# *7. Known Limitations at This Tier*

| Limitation | Description |
|------------|-------------|
| **Routing precision** | Routing becomes the primary bottleneck. A misclassified query never reaches the correct deltas, regardless of retrieval quality within a session. |
| **Session maintenance** | Poorly defined or overlapping specialty descriptions gradually reduce routing accuracy unless the confidence metrics are actively monitored. |
| **Cross-session fallback** | Fallback improves correctness at the cost of additional latency. Persistently high fallback rates usually indicate that session boundaries should be revised rather than the router retuned. |
| **Per-session specialization** | Per-domain prompts or specialized models (mentioned in `architecture.md` §5.2) are intentionally outside the scope of this tier. This layer introduces routing only. |

---

# *8. Next Steps*

- Record benchmark results for each session in `../benchmarks/results.md`.
- If a single session eventually accumulates enough deltas to require further partitioning, revisit the session design instead of introducing another architectural tier.