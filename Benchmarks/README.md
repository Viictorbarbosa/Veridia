# Veridia — Benchmarks

For the architectural comparison table (**theoretical, not yet measured**), see `../docs/architecture.md` and `../README.md`.

The comparison tables elsewhere in this repo describe **complexity classes** — what should be true by design.

This folder is where those claims get replaced with actual numbers from your own store:

- Extraction quality
- Update cost
- Query latency
- Consistency under a real update

Designed to be minimal enough to run entirely from a phone browser — no local machine, no GPU, no installed toolchain.

---

# 1. What's Included

| File / Folder | Purpose |
|---------------|---------|
| `golden_set/` | 15–30 hand-annotated documents with their expected deltas — the same golden set referenced in `docs/architecture.md` §3.1. Used to score extraction precision/recall. |
| `run_benchmark.py` | Runs the golden set through `mvp/extract.py`'s pipeline and `mvp/query.py`, timing each stage and comparing extracted deltas against the annotations. |
| `results.md` | A running log of benchmark runs — one entry per run, so numbers are comparable over time as the pipeline changes. |

---

# 2. Running From Your Phone

No local setup required — this runs entirely in a hosted notebook reachable from a mobile browser.

1. Open **Google Colab** in your phone's browser → **New notebook**.

2. Get a free **Postgres** instance — **Supabase** or **Neon** both have a free tier and give you a `DATABASE_URL` immediately after signup, with no local install.

3. In the first Colab cell, install dependencies:

```bash
!pip install psycopg2-binary python-dotenv requests
```

4. Clone the repo (or upload just the files you need) and set your secrets:

```python
import os

os.environ["DATABASE_URL"] = "postgresql://..."
os.environ["LLM_API_KEY"] = "..."
os.environ["LLM_MODEL"] = "claude-sonnet-5"

!git clone https://github.com/yourname/veridia.git
%cd veridia

!psql "$DATABASE_URL" -f mvp/schema.sql
```

> Colab's runtime is CPU-only by default — that's fine here. Nothing in Veridia needs a GPU; the only compute-heavy step is the LLM API call itself, which runs remotely.

5. Run the benchmark:

```bash
!python benchmarks/run_benchmark.py
```

6. Copy the printed summary into `results.md` (or have the notebook append to it and download the file — either works from mobile).

---

# 3. What Gets Measured

| Metric | How it's measured | Why it matters |
|--------|-------------------|----------------|
| **Grounding rejection rate** | Percentage of extracted candidates whose `source_span` wasn't found verbatim in the source. | Direct proxy for hallucination — should trend toward the annotated ground truth's own rate, not zero (zero can mean the check isn't running). |
| **Verification rejection rate** | Percentage of grounded candidates rejected by pass 2. | Flags cases where text was found but the causal claim wasn't actually supported. |

# 3. What Gets Measured *(continued)*

| Metric | How it's measured | Why it matters |
|--------|-------------------|----------------|
| **Extraction precision / recall** | Extracted deltas vs. golden set annotations, matched by `causal_key` + content similarity. | The actual quality number the rest of this repo's claims depend on. |
| **Update latency** | Time to insert one new delta, measured against stores of increasing size (e.g. 10 / 100 / 1,000 existing deltas). | Should stay roughly flat — this is the empirical test of the "**~O(1) per update**" claim. |
| **Query latency** | End-to-end time for `mvp/query.py` to answer a golden-set question. | Includes key resolution + lookup + interpretation; watch how this moves as the store grows. |
| **Consistency check** | Update a delta, immediately re-query, confirm the new value is returned with no stale read. | Pass/fail — this is the core claim of the whole architecture, so it gets a dedicated check, not just a latency number. |

---

# 4. The Golden Set

Each file in `golden_set/` is one source document plus its hand-annotated expected deltas:

```json
{
  "document": "path/to/source.txt",
  "expected_deltas": [
    {
      "causal_key": "auth.token_expiry",
      "content": "Session timeout triggers automatic logout",
      "source_span": "when the timeout expires, the user is logged out"
    }
  ]
}
```

Stratify the set across three difficulty levels, per `docs/architecture.md` §3.1:

- **Obvious** — explicit, single-sentence causal statements.
- **Ambiguous** — causal language that could be read more than one way.
- **Multi-paragraph** — the cause and effect are stated in different parts of the document.

A golden set that's all **"obvious"** cases will report inflated precision/recall — it's testing the easy 80%, not the part of the pipeline most likely to fail.

---

# 5. Recording Results

Append one entry per run to `results.md`:

```markdown
## 2026-07-06 — commit abc1234 — claude-sonnet-5

- Golden set: 22 documents, 41 expected deltas
- Grounding rejection rate: 9%
- Verification rejection rate: 4%
- Precision: 0.88 · Recall: 0.81
- Update latency (avg, n=20): 340ms
- Query latency (avg, n=20): 1.9s
- Consistency check: PASS (12/12)
```

Tracking the model name and commit matters — a number without both is **not reproducible**, and prompt or model changes are exactly what you're trying to catch regressions in.

# 6. Methodology Caveats

Being direct about what this suite **is** and **isn't**:

- A **15–30 document golden set** is a smoke test, **not** a statistically rigorous benchmark. It's enough to catch regressions and get a directional read, but not enough to publish a confidence interval.

- **LLM API latency** is **not** a controlled measurement — it varies with provider load and network conditions. Report it, but don't over-index on small differences between runs.

- No **adversarial/red-team** set is included. The golden set tests realistic documents, not inputs deliberately designed to break grounding or trigger hallucination.

- No **RAG baseline** is included by default. These numbers describe **Veridia's own behavior**, not a head-to-head comparison against an embedding-based pipeline. Building that comparison (using the same golden set and running it through a minimal RAG setup) is the natural next extension if you want the architectural comparison table to become a real benchmark instead of a theoretical one.

---

# 7. Next Steps

- Grow the golden set as real documents get processed through the MVP — don't hand-craft all 20+ examples up front if real ones are available.

- Once the **Scalable Tier** is in use, extend `run_benchmark.py` to report **per-session accuracy** alongside `confidence_test.py`'s router metrics.