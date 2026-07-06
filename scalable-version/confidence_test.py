#!/usr/bin/env python3
"""
Veridia Scalable Tier — Confidence Test
==========================================
A lightweight harness for measuring router.py's accuracy and confidence
calibration against a small labeled set, per scalable/README.md §5.

This is NOT the golden set used for delta-extraction quality (see
benchmarks/) — it's specifically about whether the ROUTER sends questions
to the right session. Re-run this every time you add, remove, or reword a
session's specialty description.

Replace LABELED_QUESTIONS below with real questions and expected session
ids from your own domains before trusting the results.

Usage:
    python confidence_test.py
    python confidence_test.py --threshold 0.8
"""

import argparse
import os
import sys

import psycopg2
from dotenv import load_dotenv

from router import classify_session, CONFIDENCE_THRESHOLD

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

# ============================================================================
# Labeled test set — REPLACE with your own (question, expected_session_id)
# pairs. Aim for 15-30 examples, stratified: obvious cases, ambiguous cases,
# and a few that should legitimately trigger a fallback (expected = None).
# ============================================================================

LABELED_QUESTIONS = [
    ("Why was the client invoiced twice for the same month?", "billing"),
    ("What happens if a payment fails after the retry limit?", "billing"),
    ("Why did the user get logged out automatically?", "auth"),
    ("What's the token expiry policy for API sessions?", "auth"),
    ("Which clause governs early contract termination?", "legal"),
    ("What's the data retention requirement under the current policy?", "legal"),
    ("What's the weather like today?", None),  # should NOT be confidently routed anywhere
]


def run(threshold: float) -> None:
    if not DATABASE_URL:
        sys.exit("DATABASE_URL is not set (check your .env file)")

    conn = psycopg2.connect(DATABASE_URL)

    correct = 0
    fallback_count = 0
    confident_correct = []
    confident_incorrect = []

    try:
        for question, expected in LABELED_QUESTIONS:
            result = classify_session(conn, question, threshold=threshold)

            # For expected=None, success means the router correctly recognized
            # it shouldn't confidently commit to any session — regardless of
            # which session_id it guessed underneath that low confidence.
            if expected is None:
                is_match = not result.is_confident
            else:
                is_match = result.is_confident and result.session_id == expected

            if is_match:
                correct += 1
            if not result.is_confident:
                fallback_count += 1
            if result.is_confident:
                (confident_correct if is_match else confident_incorrect).append(result.confidence)

            status = "OK" if is_match else "MISS"
            fallback_note = " [fallback]" if not result.is_confident else ""
            print(
                f"[{status}]{fallback_note} \"{question}\"\n"
                f"    expected={expected}  got={result.session_id}  confidence={result.confidence:.2f}"
            )
    finally:
        conn.close()

    total = len(LABELED_QUESTIONS)
    accuracy = correct / total if total else 0.0
    fallback_rate = fallback_count / total if total else 0.0

    print("\n=== Confidence Test Summary ===")
    print(f"Total questions:   {total}")
    print(f"Routing accuracy:  {accuracy:.1%}")
    print(f"Fallback rate:     {fallback_rate:.1%}")

    if confident_correct:
        avg = sum(confident_correct) / len(confident_correct)
        print(f"Avg confidence — confident AND correct:  {avg:.2f}")

    if confident_incorrect:
        avg = sum(confident_incorrect) / len(confident_incorrect)
        print(f"Avg confidence — confident BUT WRONG:    {avg:.2f}")
        print("  ^ this bucket existing at all is a calibration problem — a")
        print("    confident router should rarely be wrong (README §5).")

    if accuracy < 0.9:
        print(
            "\nWarning: routing accuracy is below 90%. Review session specialty "
            "descriptions for overlap before enabling routing in production."
        )


def main():
    parser = argparse.ArgumentParser(description="Veridia router confidence test")
    parser.add_argument("--threshold", type=float, default=CONFIDENCE_THRESHOLD)
    args = parser.parse_args()
    run(args.threshold)


if __name__ == "__main__":
    main()