# Golden Set

Starter set referenced by `../README.md` and used by `run_benchmark.py`.

Verified programmatically: every `source_span` below is a literal, character-for-character substring of its paired document — the same check `mvp/extract.py`'s grounding filter applies.

This is a seed, not the target size. **9 documents / 19 deltas** is enough to validate the format and catch obvious regressions. Grow this toward **15–30** as real documents get processed through the MVP (see `../README.md` §7).

---

# Format

One `.txt` (source document) + one `.json` (annotations) per pair:

```json
{
  "document": "golden_set/<tier>/<name>.txt",
  "difficulty": "obvious | ambiguous | multi_paragraph",
  "domain": "auth | billing | legal",
  "expected_deltas": [
    {
      "causal_key": "...",
      "content": "...",
      "source_span": "... (verbatim substring of the document)",
      "caused_by": "<causal_key> (optional — only for chained/multi_paragraph cases)",
      "note": "(optional — why this case is hard, and what a naive pipeline tends to get wrong)"
    }
  ]
}
```

`caused_by` and `note` are extensions beyond the minimal example in `../README.md` §4 — added here because they make the harder tiers (below) actually testable, not just readable.

---

# Index

| File | Domain | Deltas | Tests |
|------|--------|-------:|-------|
| `obvious/01_session_timeout.txt` | auth | 2 | Explicit single-sentence causation |
| `obvious/02_payment_retry.txt` | billing | 2 | Explicit single-sentence causation |
| `obvious/03_contract_termination.txt` | legal | 2 | Explicit single-sentence causation |
| `ambiguous/01_refund_policy.txt` | billing | 2 | Hedged causation ("typically"), correlation vs. cause |
| `ambiguous/02_inactivity_review.txt` | auth | 2 | Soft modal ("may"), negative causal claim (X does not cause Y) |
| `ambiguous/03_delay_liability.txt` | legal | 2 | Hedged causation ("could affect"), conditional qualifiers ("where applicable") |
| `multi_paragraph/01_token_rotation.txt` | auth | 3 | Two-hop causal chain across 4 paragraphs |
| `multi_paragraph/02_fraud_threshold.txt` | billing | 2 | Cause/effect separated by an unrelated distractor paragraph |
| `multi_paragraph/03_data_retention.txt` | legal | 2 | Explicit backward reference ("described above") across paragraphs |

**19 expected deltas total** — **6 obvious**, **6 ambiguous**, **7 multi-paragraph** (including one 2-hop chain).

---

# What Each Tier Is Actually Testing

## `obvious/`

The floor. If precision/recall isn't near-perfect here, the problem is in the extraction prompt itself, not in genuinely hard cases.

## `ambiguous/`

Tests whether the pipeline respects hedging language ("may", "typically", "could", "where applicable") instead of flattening it into unconditional causation.

Also includes one negative-causation case (`auth.flagging_effect`) to check the pipeline doesn't just assume "X mentioned near Y" implies "X causes Y".

## `multi_paragraph/`

Tests whether extraction connects cause and effect that are not adjacent, including:

- one case with an explicit backward reference;
- one with a two-hop chain.

Each includes a distractor paragraph between cause and effect to catch pipelines that only link within a local window.

---

# Adding New Cases

1. Write the source document first, naturally — don't write the annotation and reverse-engineer text to match it.

2. Copy the exact `source_span` text out of the document you just wrote (don't retype it — copy/paste, then verify).

3. Run the grounding check below before committing:

```python
import json
import glob

for path in glob.glob("golden_set/**/*.json", recursive=True):
    data = json.load(open(path))
    doc = open(data["document"]).read()

    for d in data["expected_deltas"]:
        assert d["source_span"] in doc, (
            f"{path}: {d['causal_key']} span not found verbatim"
        )

print("OK")
```

An annotation whose `source_span` isn't a real substring isn't testing grounding — it's testing whether you retyped the sentence correctly.