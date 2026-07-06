# *Veridia — Scalable Tier*

> For full architecture details, see `../docs/architecture.md`.
>
> For decision criteria, see `../docs/when-to-use.md`.

This tier adds **session-based routing** on top of the MVP's flat index. It exists for one reason: a single monolithic **causal-key lookup** becomes slower and more ambiguous as multiple unrelated domains (legal, ops, product, support...) accumulate deltas in the same store.

> **Don't start here.** Build the MVP first, prove the core consistency win with your own *golden set*, and only move to this tier once you've actually hit the bottleneck it solves (see `when-to-use.md` §5).

---

# *1. What's Included*

| **File** | **Purpose** |
|----------|-------------|
| `schema.sql` | Extends the MVP delta table with `session_id`, `specialty`, and `relevance_weight`, plus session-scoped indexes. Additive, not a replacement — MVP deltas keep working. |
| `router.py` | Classifies a question into a session (domain) before lookup runs, with a confidence score. Falls back to cross-session search when confidence is low. |
| `confidence_test.py` | A lightweight harness containing labeled *(question, expected_session)* pairs used to measure router accuracy before production deployment. |

---

# *2. Requirements*

Same as the MVP:

- *Python 3.10+*
- *A PostgreSQL instance*
- *An LLM API key*

This tier is a structural change, not a new piece of infrastructure.

---

# *3. Setup*

## *1. Migrating from the MVP*

Existing deltas have no `session_id`. Backfill them into a default session before enabling routing:

```sql
ALTER TABLE deltas
ADD COLUMN IF NOT EXISTS session_id TEXT;

UPDATE deltas
SET session_id = 'default'
WHERE session_id IS NULL;
```

> `schema.sql` includes this migration as part of its migration path. See the file for the complete statement set.

---

## *2. Apply the schema*

```bash
psql "$DATABASE_URL" -f schema.sql
```

---

## *3. Define your sessions*

A session consists of:

- a `session_id`;
- a short natural-language **specialty** description that the router matches questions against.

Example:

| **Session** | **Specialty** |
|------------|---------------|
| `legal` | *contract terms, compliance clauses, regulatory obligations* |

This configuration can live in either:

- a JSON file;
- a small database table.

---

## *4. Validate the router*

```bash
python confidence_test.py
```

Do **not** enable session-scoped lookup in production until the router reaches a confidence threshold you're comfortable with (see §5).

---

# *4. How It Works*

```text
Question
   │
   ▼
router.py: classify session
        │
        ├────────── Confident ──────────► Lookup within session
        │                                     │
        │                                     ▼
        │                              Interpretation
        │                                     │
        │                                     ▼
        │                                   Answer
        │
        └──── Low confidence ──────────► Cross-session lookup
                                              │
                                              ▼
                                       Interpretation
                                              │
                                              ▼
                                           Answer
```

The router runs **before** any causal-key resolution.

It first narrows the search space, then the MVP's key-resolution step (`mvp/query.py`) executes exactly as before, except it is scoped to the matched session instead of the entire store.

> Low-confidence queries **must not** silently search only the highest-scoring session. They should always fall back to a cross-session search.

A wrong-session miss is worse than a slightly slower cross-session lookup because the query would never reach the correct deltas.

---

# *5. The Confidence Test*

`confidence_test.py` reports:

| **Metric** | **Description** |
|------------|-----------------|
| **Routing accuracy** | Percentage of questions classified into the correct session. |
| **Confidence calibration** | Measures whether the router's confidence score actually correlates with correctness. A router that is confidently wrong is more dangerous than one that is uncertain and triggers fallback. |
| **Fallback rate** | Frequency of low-confidence cross-session searches. A steadily increasing fallback rate usually indicates overlapping session definitions. |

> Re-run this test whenever you add, remove, or redefine a session.

Routing accuracy is not only a property of the code—it also depends on your current session boundaries.

---

# *6. Success Criteria*

- [ ] Routing accuracy on the labeled dataset remains above your chosen threshold (start conservatively, e.g. **90%+**).
- [ ] Low-confidence queries reliably fall back to cross-session search instead of returning wrong-session answers.
- [ ] Query latency with routing enabled remains acceptable compared to the MVP's flat lookup.
- [ ] Adding a new session does not silently degrade accuracy on existing sessions (re-run `confidence_test.py` after every session change).

---

# *7. Known Limitations at This Tier*

| **Limitation** | **Description** |
|---------------|-----------------|
| **Routing precision** | Becomes the primary bottleneck. A misclassified query never reaches the correct deltas, regardless of retrieval quality within a session. |
| **Session maintenance** | Overlapping or poorly defined specialties gradually reduce router accuracy unless fallback rates are actively monitored. |
| **Cross-session fallback** | Increases latency but preserves correctness. Persistently high fallback rates usually indicate poorly scoped sessions rather than router tuning issues. |
| **Per-session specialization** | Specialized prompts or models (mentioned in `architecture.md` §5.2) are **not** included in this tier. This layer introduces routing only. |

---

# *8. Next Steps*

- Log results against your *golden set* in `../benchmarks/results.md`, split by session.
- If delta volume within a single session becomes large enough to require further partitioning, revisit session granularity instead of adding another architectural tier.