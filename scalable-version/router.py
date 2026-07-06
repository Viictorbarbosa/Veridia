#!/usr/bin/env python3
"""
Veridia Scalable Tier — Router
=================================
Classifies a question into a session (domain) before any causal-key lookup
runs, per docs/architecture.md §5.2. This is what lets lookup at this tier
narrow the search space instead of scanning every delta in the store.

Confidence matters more than the top pick: a wrong session chosen
"confidently" is worse than an uncertain result that correctly falls back to
a cross-session search (see scalable/README.md §4). This module exposes both
the classification and a confidence score explicitly — callers are expected
to check `is_confident`, not just take `session_id` at face value.

Usage as a library:
    from router import classify_session
    result = classify_session(conn, "Why was the client billed twice?")
    # result.session_id, result.confidence, result.is_confident

Usage as a CLI (manual sanity check):
    python router.py "Why was the client billed twice?"
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Optional

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-5")

# Below this, treat the classification as unreliable and fall back to a
# cross-session search rather than trusting the top pick. This default is a
# starting point — tune it against your own confidence_test.py results.
CONFIDENCE_THRESHOLD = 0.7

ROUTER_SYSTEM_PROMPT = """You are the session router for the Veridia system.

You will be given a user's question and a list of sessions, each with a
short description of its specialty (the kind of causal facts it contains).

Decide which session the question most likely belongs to. Report your
confidence as a number between 0 and 1 — be honest, not optimistic. A
confidence of 0.9+ means you're nearly certain; anything below 0.5 means
you're mostly guessing.

Respond with ONLY a JSON object, no prose, no markdown fences:

{"session_id": "legal", "confidence": 0.86, "reasoning": "one short phrase"}

If no session seems relevant, respond with:

{"session_id": null, "confidence": 0.0, "reasoning": "one short phrase"}
"""


@dataclass
class RoutingResult:
    session_id: Optional[str]
    confidence: float
    reasoning: str
    is_confident: bool


# ============================================================================
# LLM call — same pattern as mvp/extract.py and mvp/query.py.
# ============================================================================


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
            "max_tokens": 300,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}],
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return "".join(block["text"] for block in data["content"] if block["type"] == "text")


def parse_json_response(raw: str) -> dict:
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {e}\n---\n{cleaned[:500]}")


# ============================================================================
# Session catalog
# ============================================================================


def list_sessions(conn) -> list:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT session_id, specialty FROM sessions ORDER BY session_id")
        return cur.fetchall()


# ============================================================================
# Classification
# ============================================================================


def classify_session(conn, question: str, threshold: float = CONFIDENCE_THRESHOLD) -> RoutingResult:
    sessions = list_sessions(conn)
    if not sessions:
        return RoutingResult(
            session_id=None, confidence=0.0, reasoning="no sessions defined", is_confident=False
        )

    catalog = "\n".join(f"- {s['session_id']}: {s['specialty']}" for s in sessions)
    payload = f"Question: {question}\n\nSessions:\n{catalog}"

    raw = call_llm(ROUTER_SYSTEM_PROMPT, payload)
    parsed = parse_json_response(raw)

    confidence = float(parsed.get("confidence", 0.0))
    session_id = parsed.get("session_id")

    return RoutingResult(
        session_id=session_id,
        confidence=confidence,
        reasoning=parsed.get("reasoning", ""),
        is_confident=(confidence >= threshold) and (session_id is not None),
    )


# ============================================================================
# CLI
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="Veridia session router — manual sanity check")
    parser.add_argument("question", help="Natural-language question to classify")
    parser.add_argument("--threshold", type=float, default=CONFIDENCE_THRESHOLD)
    args = parser.parse_args()

    if not DATABASE_URL:
        sys.exit("DATABASE_URL is not set (check your .env file)")

    conn = psycopg2.connect(DATABASE_URL)
    try:
        result = classify_session(conn, args.question, threshold=args.threshold)
    finally:
        conn.close()

    print(f"session_id:   {result.session_id}")
    print(f"confidence:   {result.confidence:.2f}")
    print(f"reasoning:    {result.reasoning}")
    print(f"is_confident: {result.is_confident}  (threshold: {args.threshold})")
    if not result.is_confident:
        print("\n→ Falls back to cross-session search (see scalable/README.md §4)")


if __name__ == "__main__":
    main()