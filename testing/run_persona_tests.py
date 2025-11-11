#!/usr/bin/env python3
"""
Persona-focused regression runner for ClimateGPT.

This script executes a curated persona question bank against the ClimateGPT
pipeline (mcp_http_bridge + mcp_server_stdio) to verify that the four supported
personas stay aligned after prompt or persona tuning changes.

Usage:
    uv run python testing/run_persona_tests.py
    uv run python testing/run_persona_tests.py --questions 1,5 --verbose
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests

from climategpt_persona_engine import PERSONA_ORDER, process_persona_question

QUESTIONS_FILE = Path(__file__).parent / "persona_question_bank.json"
OUTPUT_DIR = Path(__file__).parent / "test_results"


def load_questions(question_filter: Optional[Iterable[int]] = None) -> List[Dict[str, Any]]:
    if not QUESTIONS_FILE.exists():
        raise FileNotFoundError(f"Persona question bank not found: {QUESTIONS_FILE}")

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    questions = payload.get("questions", [])
    if not isinstance(questions, list):
        raise ValueError("Invalid persona question bank structure (missing 'questions' list)")

    if question_filter:
        ids = set(question_filter)
        questions = [q for q in questions if int(q.get("id", 0)) in ids]

    for q in questions:
        personas = q.get("personas")
        if not personas:
            q["personas"] = PERSONA_ORDER
        else:
            q["personas"] = [p for p in personas if p in PERSONA_ORDER]

    return questions


def wait_for_mcp_server(url: str, retries: int = 30, delay: float = 1.0) -> bool:
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(delay)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run persona-focused ClimateGPT regression tests")
    parser.add_argument(
        "--questions",
        type=str,
        help="Comma-separated list of question IDs to run (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory to save test results JSON (default: testing/test_results)",
    )
    parser.add_argument(
        "--health-url",
        type=str,
        default=os.environ.get("PERSONA_MCP_HEALTH", "http://127.0.0.1:8010/health"),
        help="Health endpoint for MCP bridge",
    )
    parser.add_argument(
        "--skip-health-check",
        action="store_true",
        help="Skip MCP server health check (assumes server is already running)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output for each persona response",
    )

    args = parser.parse_args()

    if not args.skip_health_check:
        print(f"Checking MCP bridge at {args.health_url} ...", flush=True)
        if not wait_for_mcp_server(args.health_url):
            print("❌ MCP bridge not reachable. Start it with `make serve` and retry.", flush=True)
            return 1
        print("✅ MCP bridge is online.\n", flush=True)

    question_filter: Optional[List[int]] = None
    if args.questions:
        try:
            question_filter = [int(q.strip()) for q in args.questions.split(",") if q.strip()]
        except ValueError as exc:
            print(f"Invalid --questions argument: {exc}", file=sys.stderr)
            return 1

    questions = load_questions(question_filter)
    if not questions:
        print("No persona questions selected. Nothing to do.", flush=True)
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    total_runs = sum(len(q["personas"]) for q in questions)

    print(f"Running {len(questions)} question groups across {total_runs} persona evaluations...\n", flush=True)

    for idx, q in enumerate(questions, start=1):
        prompt = q["prompt"]
        personas = q["personas"]
        meta = {
            "id": q.get("id"),
            "category": q.get("category"),
            "notes": q.get("notes"),
        }

        print(f"[{idx}/{len(questions)}] Prompt #{meta['id']}: {prompt}")
        if meta["notes"]:
            print(f"   Notes: {meta['notes']}")

        for persona in personas:
            start = time.time()
            try:
                answer, data_context, used_tool = process_persona_question(prompt, persona)
                success = True
                error = None
            except Exception as exc:
                answer = None
                data_context = {}
                used_tool = "unknown"
                success = False
                error = str(exc)

            elapsed_ms = round((time.time() - start) * 1000, 2)

            if args.verbose:
                status_icon = "✅" if success else "❌"
                print(f"   {status_icon} {persona} [{elapsed_ms} ms]")
                if success and answer:
                    preview = answer if len(answer) < 220 else f"{answer[:217]}..."
                    print(f"      Answer preview: {preview}")
                elif error:
                    print(f"      Error: {error}")

            result_entry = {
                "question_id": meta["id"],
                "persona": persona,
                "prompt": prompt,
                "success": success,
                "response_time_ms": elapsed_ms,
                "used_tool": used_tool,
                "answer": answer,
                "data_context": {
                    "row_count": len(data_context.get("rows", [])) if isinstance(data_context, dict) else None,
                    "meta": data_context.get("meta") if isinstance(data_context, dict) else None,
                },
                "error": error,
                "category": meta["category"],
                "notes": meta["notes"],
                "timestamp": datetime.now().isoformat(),
            }
            results.append(result_entry)

        print()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output_dir / f"persona_results_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total_question_groups": len(questions),
                    "total_persona_runs": len(results),
                    "mcp_health_url": args.health_url,
                },
                "results": results,
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )

    print(f"🎉 Persona regression complete. Results saved to {output_path}\n", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())





