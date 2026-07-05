# Veridia — MVP

For full architecture details, see `../docs/architecture.md`.

For decision criteria, see `../docs/when-to-use.md`.

This is the minimal implementation of Veridia: a single Postgres instance, a single LLM for both extraction and query-time interpretation, no domain routing, no caching.

Its only goal is to validate the core claim — **delta-based storage stays consistent across document updates at a much lower update cost than re-indexing an equivalent RAG setup.**

Everything else (session routing, specialized indexing, meta-deltas) belongs to later tiers.

Start here first.

---

# 1. What's Included

| File | Purpose |
|------|---------|
| **schema.sql** | Delta table + unique index on **(causal_key, active=true)** for O(1)/O(log n) current-truth lookup. |
| **extract.py** | Two-pass extraction pipeline: (1) extraction against a causal checklist, (2) verification with mandatory grounding against the source text. |
| **query.py** | Looks up the active delta(s) for a causal key and runs the LLM interpretation step to produce an answer. |

---

# 2. Requirements

- Python **3.10+**
- A Postgres instance — local, or a free tier (Supabase, Neon, Railway all work and are reachable from a phone browser)
- An API key for any LLM provider with a chat-completion endpoint

```bash
pip install psycopg2-binary python-dotenv requests
```

---

# 3. Setup

## 1. Create your `.env` file

```env
DATABASE_URL=postgresql://user:password@host:port/dbname
LLM_API_KEY=your_key_here
LLM_MODEL=your_model_name
```

## 2. Apply the schema

```bash
psql "$DATABASE_URL" -f schema.sql
```

## 3. Extract deltas from a document

```bash
python extract.py --input path/to/document.txt
```

## 4. Ask a question

```bash
python query.py "Why did the session get logged out?"
```

---

# 4. How It Works

```text
document.txt
      │
      ▼
 extract.py
      │
      ▼
deltas (Postgres)
      │
      ▼
 query.py
      │
      ▼
   answer

extraction + grounding check
causal-key lookup + LLM interpretation
```

`extract.py` never overwrites a delta in place — if a `causal_key` already has an active delta, the old one is marked `active = false` and the new one becomes the current truth, preserving full history.

`query.py` does **not** embed the question or run a vector search. It resolves the question to a `causal_key` (or a small set of candidate keys) and reads directly from the index.

---

# 5. Success Criteria

Before considering the MVP validated, confirm:

- [ ] Updating a source document and re-running `extract.py` produces a new active delta, and the old version is preserved but inactive — not deleted, not duplicated as a conflicting entry.
- [ ] A query issued right after an update returns the new fact, with no inconsistency window.
- [ ] Re-running extraction on an unchanged document does not produce duplicate deltas for the same causal key.
- [ ] Grounding rejection rate is being logged — even informally — as your first quality signal.

---

# 6. Known Limitations at This Tier

- Single model for extraction and verification. The dual-model refinement that reduces correlated hallucination (see `architecture.md` §3.1) is not applied here — treat MVP-stage grounding as a first filter, not a final guarantee.
- No caching. Every query re-runs the LLM interpretation step. Fine at low query volume; revisit before scaling query traffic.
- No domain routing. A single flat index works until you have multiple unrelated domains competing for the same `causal_key` space — at that point, move to `scalable/`.
- No periodic reconciliation pass. Contradictions between deltas from different documents are not automatically detected at this tier.

---

# 7. Next Steps

Run the MVP against your own golden set and log results in `benchmarks/results.md`.

Once a single domain outgrows a flat index, move to `scalable/README.md`.