#!/usr/bin/env python3
"""
Veridia MVP — Query Pipeline
=============================
Answers a natural-language question using the delta store, per
docs/architecture.md §4:

  User question ─▶ Key resolution ─▶ Lookup (+ 1-hop causal chain) ─▶ Interpretation ─▶ Answer

Retrieval never embeds the question or runs a vector search:

  1. Key resolution (LLM)    The question is matched against the list of known
                             causal_keys (and their current content) to find
                             which key(s) it's actually about.
  2. Lookup (deterministic)  The active delta for each matched key is fetched,
                             along with its direct cause and effects — one hop
                             of the causal chain, for context.
  3. Interpretation (LLM)   The retrieved delta(s) are handed to the model to
                             synthesize a direct answer to the original question.

MVP-tier note: step 1 scans every distinct causal_key in the store to find a
match. That's fine at small scale, but it's exactly the bottleneck the
Scalable tier's session routing (docs/architecture.md §5.2) exists to remove.

Usage:
    python query.py "Why did the session get logged out?"
    python query.py "Why did the session get logged out?" --verbose
    python query.py "What was the timeout policy?" --as-of 2026-02-01
"""

import argparse
import json
import os
import re
import sys

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-5")

# ============================================================================
# Prompts
# ============================================================================

KEY_RESOLUTION_SYSTEM_PROMPT = """You are the retrieval layer for the Veridia system.

You will be given a user's question and a list of every causal_key currently
in the store, each with a one-line summary of its content.

Identify which causal_key(s) the question is actually about. Pick as few as
possible — only keys that are directly relevant. If nothing in the list is
relevant, return an empty array.

Respond with ONLY a JSON array of causal_key strings, no prose, no markdown fences:

["auth.token_expiry", "auth.session_state"]
"""

INTERPRETATION_SYSTEM_PROMPT = """You are the interpretation layer for the Veridia system.

You will be given a user's question and a set of retrieved deltas — atomic,
versioned causal facts. Answer the question directly, using only the
information in the deltas provided. If the question asks "why" or "what
happens if", connect the cause-and-effect chain explicitly. If the deltas
don't contain enough information to answer, say so plainly instead of
guessing.

Keep the answer concise — a few sentences, not a report.
"""


# ============================================================================
# LLM call
# ============================================================================
# Same pattern as extract.py. Targets the Anthropic Messages API — rewrite
# this function's body to use a different provider.


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
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}],
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return "".join(block["text"] for block in data["content"] if block["type"] == "text")


def parse_json_response(raw: str) -> list:
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {e}\n---\n{cleaned[:500]}")


# ============================================================================
# Step 1: key resolution
# ============================================================================


def list_known_keys(conn, as_of=None) -> list:
    """
    Every distinct causal_key with a content preview. Without --as-of, reads
    from the current_truth view. With --as-of, reconstructs what each key's
    content was at that point in time (one row per key, latest version <= as_of).
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if as_of:
            cur.execute(
                """
                SELECT DISTINCT ON (causal_key) causal_key, content, created_at
                FROM deltas
                WHERE created_at <= %s
                ORDER BY causal_key, created_at DESC
                """,
                (as_of,),
            )
        else:
            cur.execute(
                "SELECT causal_key, content, created_at FROM current_truth ORDER BY causal_key"
            )
        return cur.fetchall()


def resolve_keys(question: str, known_keys: list) -> list:
    if not known_keys:
        return []

    catalog = "\n".join(f"- {row['causal_key']}: {row['content']}" for row in known_keys)
    payload = f"Question: {question}\n\nKnown causal_keys:\n{catalog}"
    raw = call_llm(KEY_RESOLUTION_SYSTEM_PROMPT, payload)
    return parse_json_response(raw)


# ============================================================================
# Step 2: lookup + one-hop causal chain
# ============================================================================


def fetch_delta_by_key(conn, causal_key: str, as_of=None):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if as_of:
            cur.execute("SELECT * FROM truth_as_of(%s, %s)", (causal_key, as_of))
        else:
            cur.execute("SELECT * FROM current_truth WHERE causal_key = %s", (causal_key,))
        return cur.fetchone()


def fetch_delta_by_id(conn, delta_id):
    """
    Fetches a specific delta by its immutable id, regardless of whether it is
    still the active version for its own causal_key. This is deliberate: a
    cause/effect link points at a specific node in the causal graph, not at
    "whatever is current truth for that key today".
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM deltas WHERE id = %s::uuid", (delta_id,))
        return cur.fetchone()


def gather_context(conn, matched_keys: list, as_of=None) -> list:
    """
    For each matched causal_key, fetch its (current or as-of) delta plus one
    hop of causal chain — its direct cause and direct effects — enough for
    the interpretation step to connect a cause to a downstream effect without
    loading the whole store.
    """
    seen_ids = set()
    context = []

    for key in matched_keys:
        delta = fetch_delta_by_key(conn, key, as_of=as_of)
        if not delta or delta["id"] in seen_ids:
            continue
        context.append(delta)
        seen_ids.add(delta["id"])

        if delta.get("cause"):
            cause_delta = fetch_delta_by_id(conn, delta["cause"])
            if cause_delta and cause_delta["id"] not in seen_ids:
                context.append(cause_delta)
                seen_ids.add(cause_delta["id"])

        for effect_id in delta.get("effect") or []:
            effect_delta = fetch_delta_by_id(conn, effect_id)
            if effect_delta and effect_delta["id"] not in seen_ids:
                context.append(effect_delta)
                seen_ids.add(effect_delta["id"])

    return context


# ============================================================================
# Step 3: interpretation
# ============================================================================


def build_context_block(deltas: list) -> str:
    lines = []
    for d in deltas:
        lines.append(
            f"- causal_key: {d['causal_key']}\n"
            f"  content: {d['content']}\n"
            f"  as of: {d['created_at']}"
        )
    return "\n".join(lines)


def interpret(question: str, deltas: list) -> str:
    if not deltas:
        return "No relevant deltas found in the store for this question."

    payload = f"Question: {question}\n\nRetrieved deltas:\n{build_context_block(deltas)}"
    return call_llm(INTERPRETATION_SYSTEM_PROMPT, payload)


# ============================================================================
# Main
# ============================================================================


def run(question: str, as_of=None, verbose: bool = False) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    try:
        known_keys = list_known_keys(conn, as_of=as_of)
        matched_keys = resolve_keys(question, known_keys)

        if verbose:
            print(f"Known causal_keys in store: {len(known_keys)}")
            print(f"Matched: {matched_keys}\n")

        context = gather_context(conn, matched_keys, as_of=as_of)

        if verbose:
            print("Retrieved deltas:")
            for d in context:
                print(f"  - {d['causal_key']}: {d['content']}")
            print()

        answer = interpret(question, context)

        if as_of:
            print(f"[as of {as_of}]")
        print(answer)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Veridia MVP query pipeline")
    parser.add_argument("question", help="Natural-language question")
    parser.add_argument(
        "--as-of",
        default=None,
        help="Reconstruct the answer as of this date/timestamp (e.g. 2026-02-01), "
             "using docs/architecture.md's temporal-reconstruction capability",
    )
    parser.add_argument("--verbose", action="store_true", help="Show resolved keys and retrieved deltas")
    args = parser.parse_args()

    if not DATABASE_URL:
        sys.exit("DATABASE_URL is not set (check your .env file)")

    run(args.question, as_of=args.as_of, verbose=args.verbose)


if __name__ == "__main__":
    main()