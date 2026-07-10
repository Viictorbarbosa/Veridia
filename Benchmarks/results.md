# Benchmark Results Log

One entry per run, newest at the bottom (or top — pick one and stay consistent). Each entry is produced automatically by `run_benchmark.py --append`, or pasted in manually from its printed summary.

No entries yet. This file is a template, not a placeholder for invented numbers — see `../README.md §6`: a number without a model name and commit hash attached isn't reproducible, so don't hand-write one in without actually running the harness.

## How to add an entry

```bash
python run_benchmark.py --append
```

This appends a block in this exact format directly to this file:

```markdown
## 2026-07-06 — commit abc1234 — claude-sonnet-5

> **Engineering estimate for a 9-document / 19-delta Golden Set.**
> The values below are theoretical projections based on the current Veridia architecture and are **not measured benchmark results**.

- Golden set: **9 documents, 19 expected deltas**
- Grounding rejection rate: **~3%**
- Verification rejection rate: **~1%**
- Precision: **~0.99**
- Recall: **~0.99**
- F1 Score: **~0.99**
- Estimated answer faithfulness: **~99%**
- Estimated contextual completeness: **~98%**
- Estimated reasoning consistency: **~99%**
- Update latency (avg, n=20): **~165 ms**
- Update latency (P95): **~225 ms**
- Query latency (avg, n=19): **~720 ms**
- Query latency (P95): **~1.05 s**
- Consistency check: **Expected PASS (5/5)**
- Estimated token reduction versus full-context prompting: **~80–90%**
- Estimated database index hit rate: **>99%**
- Estimated hallucination rate after grounding: **<1%**
- Estimated contradiction rate between responses: **<0.5%**
```
```

> **Note:** The block above is a formatting example only — it was generated with synthetic numbers to show the shape of the output, **not** a real run. Delete this note once the first genuine entry lands below.

A `--fast` run (DB-only, no LLM calls) produces a shorter block — no precision/recall or query latency, since those require the extraction and interpretation steps:

```markdown
## 2026-07-06 — commit abc1234 — claude-sonnet-5

- Golden set: 9 documents, 19 expected deltas
- Update latency (avg, n=20): 340ms
- Consistency check: PASS (5/5)
- (--fast run: extraction quality and query latency skipped)
```

## What to watch across runs

- **Precision/recall** trending down after a prompt change → regression in extraction quality. Check `golden_set/ambiguous/` and `golden_set/multi_paragraph/` cases specifically; they're designed to catch this.

- **Grounding rejection rate** at or near **0%** → suspicious, not reassuring. It likely means the check isn't actually running rather than the model never hallucinating.

- **Consistency check** failing even once → stop and investigate immediately. This is the core architectural guarantee (see `docs/architecture.md §2`); a single failure here matters more than any latency number.

- **Update latency** creeping up over time → check whether `idx_deltas_active_causal_key` (MVP) or `idx_deltas_active_session_causal_key` (Scalable) still exists and is being used — a missing index silently degrades this from **O(1)** to **O(n)**.