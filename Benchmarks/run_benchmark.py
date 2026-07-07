#!/usr/bin/env python3
"""
Veridia Benchmarks — Runner
=============================
Runs the golden set through the MVP pipeline and produces the metrics
described in benchmarks/README.md §3:

  - Extraction quality (LLM)   grounding/verification rejection rate,
                               precision/recall vs. golden_set annotations
  - Update latency (DB only)   single-delta insert timing, no LLM involved
  - Query latency (LLM)        end-to-end mvp/query.py pipeline timing
  - Consistency check (DB only) update -> immediate re-query, no stale read

DB-only tests (update latency, consistency) never call the LLM — they test
the trigger-based versioning in schema.sql directly. LLM tests (extraction
quality, query latency) reuse the actual functions from mvp/extract.py and
mvp/query.py, not reimplementations, so this measures the real pipeline.

Usage:
    python run_benchmark.py                  # full run
    python run_benchmark.py --fast            # DB-only: skip LLM tests
    python run_benchmark.py --append          # also append summary to results.md
"""

import argparse
import datetime as dt
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "mvp"))

import extract as extraction      # mvp/extract.py
import query as query_pipeline    # mvp/query.py

DATABASE_URL = os.environ.get("DATABASE_URL")
GOLDEN_SET_DIR = Path(__file__).resolve().parent / "golden_set"
RESULTS_PATH = Path(__file__).resolve().parent / "results.md"

MATCH_THRESHOLD = 0.5  # Jaccard word-overlap threshold to count as a match — see match_candidates()


# ============================================================================
# Golden set loading
# ============================================================================


def load_golden_set() -> list:
    """
    Returns a list of (document_text, annotation_dict) tuples. Each JSON's
    `document` field is a filename resolved relative to the JSON's own
    directory — deliberately not repo-root-relative, so golden_set/ stays
    portable regardless of where it's mounted in the tree.
    """
    pairs = []
    for json_path in sorted(GOLDEN_SET_DIR.rglob("*.json")):
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        doc_path = json_path.parent / data["document"]
        with open(doc_path, encoding="utf-8") as f:
            doc_text = f.read()
        pairs.append((doc_text, data))
    return pairs


# ============================================================================
# Matching heuristic (no embeddings — consistent with the rest of Veridia)
# ============================================================================


def word_overlap(a: str, b: str) -> float:
    """
    Jaccard similarity over lowercased word sets — a cheap, dependency-free
    proxy for "these two spans are about the same thing". Imperfect: penalizes
    paraphrasing, rewards shared boilerplate. Good enough to auto-flag likely
    matches on a small golden set; not a substitute for spot-checking misses.
    """
    wa = set(re.findall(r"\w+", a.lower()))
    wb = set(re.findall(r"\w+", b.lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def match_candidates(accepted_candidates: list, expected_deltas: list) -> tuple:
    """
    Greedy one-to-one matching between accepted extraction candidates and
    golden-set expected deltas, scored by source_span word overlap (not
    causal_key string equality — the model isn't expected to reproduce the
    exact same key names as the annotator chose).

    Returns (matched_expected_indices, matched_candidate_indices).
    """
    pairs = []
    for ei, exp in enumerate(expected_deltas):
        for ci, cand in enumerate(accepted_candidates):
            score = word_overlap(exp["source_span"], cand.source_span)
            if score >= MATCH_THRESHOLD:
                pairs.append((score, ei, ci))

    pairs.sort(reverse=True)
    matched_expected, matched_candidates = set(), set()
    for _, ei, ci in pairs:
        if ei in matched_expected or ci in matched_candidates:
            continue
        matched_expected.add(ei)
        matched_candidates.add(ci)

    return matched_expected, matched_candidates


# ============================================================================
# Extraction quality (LLM — reuses mvp/extract.py directly)
# ============================================================================


def run_extraction_quality(golden_set: list) -> dict:
    totals = {
        "extracted": 0,
        "grounding_rejected": 0,
        "verification_rejected": 0,
        "predicted_accepted": 0,
        "expected_total": 0,
        "true_positives": 0,
    }

    for doc_text, data in golden_set:
        candidates = extraction.extract_candidates(doc_text)
        totals["extracted"] += len(candidates)

        candidates = extraction.apply_grounding_filter(doc_text, candidates)
        totals["grounding_rejected"] += sum(1 for c in candidates if not c.grounded)

        candidates = extraction.verify_candidates(doc_text, candidates)
        totals["verification_rejected"] += sum(1 for c in candidates if c.grounded and not c.verified)

        accepted = [c for c in candidates if c.grounded and c.verified]
        totals["predicted_accepted"] += len(accepted)

        expected = data["expected_deltas"]
        totals["expected_total"] += len(expected)

        matched_expected, _ = match_candidates(accepted, expected)
        totals["true_positives"] += len(matched_expected)

    precision = totals["true_positives"] / totals["predicted_accepted"] if totals["predicted_accepted"] else 0.0
    recall = totals["true_positives"] / totals["expected_total"] if totals["expected_total"] else 0.0

    return {**totals, "precision": precision, "recall": recall}


# ============================================================================
# Update latency (DB only — no LLM)
# ============================================================================


def run_update_latency(conn, n: int = 20) -> list:
    """
    Times N single-delta inserts directly against the deltas table. Isolates
    the DB-level update cost the "~O(1) per update" claim in
    docs/architecture.md is about, independent of extraction/LLM speed.
    """
    latencies = []
    with conn.cursor() as cur:
        for i in range(n):
            key = f"benchmark.update_latency.{i}"
            start = time.perf_counter()
            cur.execute(
                "INSERT INTO deltas (causal_key, content, active) VALUES (%s, %s, true)",
                (key, "benchmark filler content"),
            )
            conn.commit()
            latencies.append(time.perf_counter() - start)

        cur.execute("DELETE FROM deltas WHERE causal_key LIKE 'benchmark.update_latency.%%'")
    conn.commit()
    return latencies


# ============================================================================
# Consistency check (DB only — no LLM)
# ============================================================================


def run_consistency_check(conn, trials: int = 5) -> dict:
    """
    For each trial: insert an "old" delta, confirm it reads back as current
    truth, insert a "new" delta for the SAME causal_key (triggering
    supersede_previous_delta), then immediately confirm the new value is
    returned — zero polling, zero delay. Tests the trigger-based versioning
    in schema.sql directly; no LLM involved.
    """
    passed = 0
    details = []

    with conn.cursor() as cur:
        for i in range(trials):
            key = f"benchmark.consistency.{i}"

            cur.execute("INSERT INTO deltas (causal_key, content, active) VALUES (%s, %s, true)", (key, "old value"))
            conn.commit()
            cur.execute("SELECT content FROM deltas WHERE causal_key = %s AND active = true", (key,))
            before = cur.fetchone()

            cur.execute("INSERT INTO deltas (causal_key, content, active) VALUES (%s, %s, true)", (key, "new value"))
            conn.commit()
            cur.execute("SELECT content FROM deltas WHERE causal_key = %s AND active = true", (key,))
            after = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM deltas WHERE causal_key = %s AND active = true", (key,))
            active_count = cur.fetchone()[0]

            ok = (
                before is not None and before[0] == "old value"
                and after is not None and after[0] == "new value"
                and active_count == 1
            )
            passed += int(ok)
            details.append({"key": key, "passed": ok})

        cur.execute("DELETE FROM deltas WHERE causal_key LIKE 'benchmark.consistency.%%'")
    conn.commit()

    return {"trials": trials, "passed": passed, "details": details}


# ============================================================================
# Query latency (LLM — reuses mvp/query.py directly)
# ============================================================================


def seed_ground_truth(conn, golden_set: list) -> None:
    """
    Writes the golden set's expected_deltas directly (bypassing extraction)
    under a `benchmark.seed.` prefix, so query latency measures the QUERY
    path against known-correct data, not extraction quality a second time.
    """
    with conn.cursor() as cur:
        for _, data in golden_set:
            for delta in data["expected_deltas"]:
                key = f"benchmark.seed.{delta['causal_key']}"
                cur.execute(
                    "INSERT INTO deltas (causal_key, content, source_span, active) VALUES (%s, %s, %s, true)",
                    (key, delta["content"], delta["source_span"]),
                )
    conn.commit()


def cleanup_seed(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM deltas WHERE causal_key LIKE 'benchmark.seed.%%'")
    conn.commit()


def run_query_latency(conn, golden_set: list) -> list:
    latencies = []
    for _, data in golden_set:
        for tq in data.get("test_questions", []):
            start = time.perf_counter()
            known_keys = query_pipeline.list_known_keys(conn)
            matched = query_pipeline.resolve_keys(tq["question"], known_keys)
            context = query_pipeline.gather_context(conn, matched)
            query_pipeline.interpret(tq["question"], context)
            latencies.append(time.perf_counter() - start)
    return latencies


# ============================================================================
# Stats + reporting
# ============================================================================


def summarize(latencies: list) -> dict:
    if not latencies:
        return {"avg": None, "median": None, "p95": None, "n": 0}
    ordered = sorted(latencies)
    p95_idx = min(int(len(ordered) * 0.95), len(ordered) - 1)
    return {
        "avg": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "p95": ordered[p95_idx],
        "n": len(latencies),
    }


def get_git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5, cwd=REPO_ROOT
        )
        commit = result.stdout.strip()
        return commit if commit else "unknown"
    except Exception:
        return "unknown"


def format_report(report: dict, fast: bool) -> str:
    date = dt.date.today().isoformat()
    commit = get_git_commit()
    model = os.environ.get("LLM_MODEL", "unknown")

    lines = [f"## {date} — commit {commit} — {model}", ""]
    lines.append(f"- Golden set: {report['golden_set_docs']} documents, {report['golden_set_deltas']} expected deltas")

    if not fast:
        ext = report["extraction"]
        gr_rate = ext["grounding_rejected"] / ext["extracted"] if ext["extracted"] else 0.0
        vr_rate = ext["verification_rejected"] / ext["extracted"] if ext["extracted"] else 0.0
        lines.append(f"- Grounding rejection rate: {gr_rate:.0%}")
        lines.append(f"- Verification rejection rate: {vr_rate:.0%}")
        lines.append(f"- Precision: {ext['precision']:.2f} · Recall: {ext['recall']:.2f}")

    ul = report["update_latency"]
    if ul["n"]:
        lines.append(f"- Update latency (avg, n={ul['n']}): {ul['avg']*1000:.0f}ms")

    if not fast:
        ql = report["query_latency"]
        if ql["n"]:
            lines.append(f"- Query latency (avg, n={ql['n']}): {ql['avg']:.1f}s")

    c = report["consistency"]
    status = "PASS" if c["passed"] == c["trials"] else "FAIL"
    lines.append(f"- Consistency check: {status} ({c['passed']}/{c['trials']})")

    if fast:
        lines.append("- (--fast run: extraction quality and query latency skipped)")

    return "\n".join(lines)


def append_to_results_md(report: dict, fast: bool) -> None:
    block = format_report(report, fast=fast)
    with open(RESULTS_PATH, "a", encoding="utf-8") as f:
        f.write("\n" + block + "\n")


# ============================================================================
# Main
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="Veridia benchmark runner")
    parser.add_argument("--fast", action="store_true", help="DB-only: skip extraction quality and query latency (no LLM calls)")
    parser.add_argument("--update-trials", type=int, default=20)
    parser.add_argument("--consistency-trials", type=int, default=5)
    parser.add_argument("--append", action="store_true", help="Append this run's summary to results.md")
    args = parser.parse_args()

    if not DATABASE_URL:
        sys.exit("DATABASE_URL is not set (check your .env file)")

    golden_set = load_golden_set()
    report = {
        "golden_set_docs": len(golden_set),
        "golden_set_deltas": sum(len(d["expected_deltas"]) for _, d in golden_set),
    }
    print(f"Loaded golden set: {report['golden_set_docs']} documents, {report['golden_set_deltas']} expected deltas.\n")

    conn = psycopg2.connect(DATABASE_URL)
    try:
        print("--- Update latency (DB only) ---")
        report["update_latency"] = summarize(run_update_latency(conn, n=args.update_trials))
        print(report["update_latency"])

        print("\n--- Consistency check (DB only) ---")
        report["consistency"] = run_consistency_check(conn, trials=args.consistency_trials)
        print(f"{report['consistency']['passed']}/{report['consistency']['trials']} passed")

        if not args.fast:
            print("\n--- Extraction quality (LLM) ---")
            report["extraction"] = run_extraction_quality(golden_set)
            print(report["extraction"])

            print("\n--- Query latency (LLM) ---")
            seed_ground_truth(conn, golden_set)
            try:
                report["query_latency"] = summarize(run_query_latency(conn, golden_set))
            finally:
                cleanup_seed(conn)
            print(report["query_latency"])
        else:
            print("\n--fast: skipping extraction quality and query latency (LLM-based tests)")
    finally:
        conn.close()

    print("\n=== Summary (paste into results.md) ===")
    summary = format_report(report, fast=args.fast)
    print(summary)

    if args.append:
        append_to_results_md(report, fast=args.fast)
        print(f"\nAppended to {RESULTS_PATH}")


if __name__ == "__main__":
    main()