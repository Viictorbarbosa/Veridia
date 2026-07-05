#!/usr/bin/env python3
"""
Veridia MVP — Extraction Pipeline
==================================
Two-pass delta extraction from a source document, per docs/architecture.md §3.

  Pass 1  (LLM)            Extract candidate deltas against a fixed causal checklist.
  Filter  (deterministic)  Reject any candidate whose `source_span` isn't a literal
                            substring of the source window — the grounding check
                            described in docs/architecture.md §3.1. No LLM call.
  Pass 2  (LLM)            Verify the grounded candidates: confirm the CONTENT and
                            CAUSAL CLAIM are actually supported by the source_span,
                            not just present near it.

Accepted deltas are INSERTed into Postgres. The `supersede_previous_delta` trigger
(schema.sql) handles versioning automatically — this script never UPDATEs a delta
in place.

MVP-tier note: both passes use the SAME model. The dual-model refinement that
reduces correlated hallucination (architecture.md §3.1) is not applied here —
see scalable/ for that.

Usage:
    python extract.py --input path/to/document.txt
    python extract.py --input path/to/document.txt --dry-run
"""

import argparse
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from typing import Optional

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-5")

WINDOW_TOKEN_TARGET = 3500       # aim for the middle of the 2k-5k token window
CHARS_PER_TOKEN_ESTIMATE = 4     # rough heuristic — avoids a tokenizer dependency at MVP tier

# ============================================================================
# Prompts
# ============================================================================

EXTRACTION_SYSTEM_PROMPT = """You are a causal-relationship extractor for the Veridia system.

Read the document window below and extract every distinct causal fact or event as
a "delta". For EACH delta, provide:

  1. local_id     - a short local label for this delta within this window (e.g. "d1")
  2. causal_key   - a short, stable dot-notation identifier (e.g. "auth.token_expiry")
  3. content      - one sentence stating the fact or event, in your own words
  4. source_span  - the EXACT substring from the document that supports this delta,
                     copied verbatim, character-for-character. Do not paraphrase this field.
  5. caused_by    - the local_id of another delta in THIS window that causes this one,
                     or null if there is no such relationship in this window

Only extract relationships that are explicitly stated or directly implied by the text.
Do not infer causal relationships that require outside knowledge.

Respond with ONLY a JSON array, no prose, no markdown fences:

[
  {"local_id": "d1", "causal_key": "...", "content": "...", "source_span": "...", "caused_by": null}
]

If the window contains no extractable causal facts, respond with an empty array: []
"""

VERIFICATION_SYSTEM_PROMPT = """You are a verifier for the Veridia extraction pipeline.

You will receive the original document window and a list of candidate deltas that
already passed a literal grounding check (their source_span is confirmed to appear
verbatim in the document). Your job is different from grounding: check whether the
CONTENT and CAUSAL CLAIM of each delta is actually supported by its source_span, not
just present near it.

Reject a candidate if:
  - the source_span exists in the text, but the claimed causal relationship is not
    actually stated by that span (two unrelated facts got connected)
  - the content overstates, distorts, or adds detail beyond what the source_span says

Respond with ONLY a JSON array, no prose, no markdown fences:

[
  {"local_id": "d1", "verdict": "accept"},
  {"local_id": "d2", "verdict": "reject", "reason": "..."}
]
"""

# ============================================================================
# Data model
# ============================================================================


@dataclass
class Candidate:
    local_id: str
    causal_key: str
    content: str
    source_span: str
    caused_by: Optional[str] = None
    grounded: bool = False
    verified: bool = False
    reject_reason: Optional[str] = None


# ============================================================================
# LLM call
# ============================================================================
# Targets the Anthropic Messages API. To use a different provider, rewrite the
# body of this function — everything downstream just expects a plain string back.


def call_llm(system_prompt: str, user_content: str) -> str:
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is not set (check your .env file)")

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": LLM_API_KEY,
            "anthropic-version": "2023-06-01",  # check docs.claude.com/en/api if this ever errors
            "content-type": "application/json",
        },
        json={
            "model": LLM_MODEL,
            "max_tokens": 2000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}],
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return "".join(block["text"] for block in data["content"] if block["type"] == "text")


def parse_json_response(raw: str) -> list:
    """Strip stray markdown fences the model sometimes adds despite instructions."""
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {e}\n---\n{cleaned[:500]}")


# ============================================================================
# Windowing
# ============================================================================


def split_into_windows(text: str, target_tokens: int = WINDOW_TOKEN_TARGET) -> list:
    """
    Splits on paragraph boundaries, packing paragraphs into windows close to the
    target size. Token count is approximated as char_count / 4 — no tokenizer
    dependency at MVP tier. Keeps each window within the 2k-5k token range
    described in docs/architecture.md §3.
    """
    target_chars = target_tokens * CHARS_PER_TOKEN_ESTIMATE
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    windows, current, current_len = [], [], 0

    for para in paragraphs:
        if current_len + len(para) > target_chars and current:
            windows.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(para)
        current_len += len(para)

    if current:
        windows.append("\n\n".join(current))

    return windows or [text]


# ============================================================================
# Pipeline stages
# ============================================================================


def extract_candidates(window: str) -> list:
    raw = call_llm(EXTRACTION_SYSTEM_PROMPT, window)
    items = parse_json_response(raw)
    return [
        Candidate(
            local_id=item["local_id"],
            causal_key=item["causal_key"],
            content=item["content"],
            source_span=item["source_span"],
            caused_by=item.get("caused_by"),
        )
        for item in items
    ]


def apply_grounding_filter(window: str, candidates: list) -> list:
    """
    Deterministic check — no LLM call. Rejects any candidate whose source_span
    is not a literal substring of the window. This is the "near-deterministic"
    check described in docs/architecture.md §3.1, and the cheapest possible
    defense against hallucination.
    """
    for c in candidates:
        c.grounded = c.source_span.strip() in window
    return candidates


def verify_candidates(window: str, candidates: list) -> list:
    grounded = [c for c in candidates if c.grounded]
    if not grounded:
        return candidates

    payload = json.dumps({
        "document": window,
        "candidates": [
            {"local_id": c.local_id, "content": c.content, "source_span": c.source_span}
            for c in grounded
        ],
    })
    raw = call_llm(VERIFICATION_SYSTEM_PROMPT, payload)
    verdicts = {v["local_id"]: v for v in parse_json_response(raw)}

    for c in grounded:
        verdict = verdicts.get(c.local_id, {"verdict": "reject", "reason": "no verdict returned"})
        c.verified = verdict.get("verdict") == "accept"
        if not c.verified:
            c.reject_reason = verdict.get("reason", "rejected by verifier")

    return candidates


# ============================================================================
# Persistence
# ============================================================================


def write_deltas(conn, candidates: list) -> int:
    accepted = [c for c in candidates if c.grounded and c.verified]
    if not accepted:
        return 0

    local_to_uuid = {}
    with conn.cursor() as cur:
        # First pass: insert every accepted delta, capturing its generated UUID.
        # No cause link yet — all UUIDs need to exist before wiring references.
        for c in accepted:
            new_id = str(uuid.uuid4())
            local_to_uuid[c.local_id] = new_id
            cur.execute(
                """
                INSERT INTO deltas (id, causal_key, content, source_span, active)
                VALUES (%s, %s, %s, %s, true)
                """,
                (new_id, c.causal_key, c.content, c.source_span),
            )

        # Second pass: wire up cause/effect now that every UUID in this batch exists.
        for c in accepted:
            if c.caused_by and c.caused_by in local_to_uuid:
                cur.execute(
                    "UPDATE deltas SET cause = %s::uuid WHERE id = %s::uuid",
                    (local_to_uuid[c.caused_by], local_to_uuid[c.local_id]),
                )
                cur.execute(
                    "UPDATE deltas SET effect = array_append(effect, %s::uuid) WHERE id = %s::uuid",
                    (local_to_uuid[c.local_id], local_to_uuid[c.caused_by]),
                )

    conn.commit()
    return len(accepted)


# ============================================================================
# Main
# ============================================================================


def run(input_path: str, dry_run: bool = False) -> None:
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    windows = split_into_windows(text)
    print(f"Split document into {len(windows)} window(s).")

    conn = None if dry_run else psycopg2.connect(DATABASE_URL)
    totals = {"extracted": 0, "grounding_rejected": 0, "verification_rejected": 0, "inserted": 0}

    try:
        for i, window in enumerate(windows, start=1):
            print(f"\n--- Window {i}/{len(windows)} ---")

            candidates = extract_candidates(window)
            totals["extracted"] += len(candidates)

            candidates = apply_grounding_filter(window, candidates)
            grounding_rejected = [c for c in candidates if not c.grounded]
            totals["grounding_rejected"] += len(grounding_rejected)
            for c in grounding_rejected:
                print(f"  [grounding-rejected] {c.local_id}: source_span not found verbatim")

            candidates = verify_candidates(window, candidates)
            verification_rejected = [c for c in candidates if c.grounded and not c.verified]
            totals["verification_rejected"] += len(verification_rejected)
            for c in verification_rejected:
                print(f"  [verification-rejected] {c.local_id}: {c.reject_reason}")

            accepted = [c for c in candidates if c.grounded and c.verified]

            if dry_run:
                for c in accepted:
                    print(f"  [would insert] {c.causal_key}: {c.content}")
                totals["inserted"] += len(accepted)
            else:
                inserted = write_deltas(conn, candidates)
                totals["inserted"] += inserted
                print(f"  Inserted {inserted} delta(s).")
    finally:
        if conn:
            conn.close()

    print("\n=== Summary ===")
    print(f"Extracted:               {totals['extracted']}")
    print(f"Rejected (grounding):     {totals['grounding_rejected']}")
    print(f"Rejected (verification):  {totals['verification_rejected']}")
    print(f"Inserted:                 {totals['inserted']}")
    if totals["extracted"]:
        rejection_rate = 1 - (totals["inserted"] / totals["extracted"])
        print(f"Overall rejection rate:   {rejection_rate:.1%}  "
              f"(log this — it's your quality signal, see mvp/README.md §5)")


def main():
    parser = argparse.ArgumentParser(description="Veridia MVP extraction pipeline")
    parser.add_argument("--input", required=True, help="Path to the source document (.txt)")
    parser.add_argument("--dry-run", action="store_true", help="Run extraction without writing to Postgres")
    args = parser.parse_args()

    if not args.dry_run and not DATABASE_URL:
        sys.exit("DATABASE_URL is not set (check your .env file), or pass --dry-run")

    run(args.input, dry_run=args.dry_run)


if __name__ == "__main__":
    main()