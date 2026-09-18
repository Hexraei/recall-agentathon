"""Which free model can actually hold the contract, and how fast.

    python bakeoff.py                 the shortlist, 2 trials each
    python bakeoff.py --trials 5      more confidence, more time
    python bakeoff.py --all           every free model on OpenRouter

Zero budget: only `:free` models are tested. A model that is not free is not a
candidate however good it is.

Measured on the real extraction prompt with a real submission, because a model
that parses a toy schema and fails this one has told you nothing. Three things
are scored, and the third is the one that decides it:

  parse      did a valid EvidenceSet come back at all
  latency    seconds per call - four calls per run, so multiply by four
  verbatim   did every passage actually appear in the submission

`verbatim` is the killer. A model that paraphrases produces fluent evidence that
the citation check demotes, and then extraction yields nothing supported. One
clean run is an anecdote; two runs disagreeing is data, so the default is two
trials and you should raise it before trusting a winner.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time

import httpx

from app import fixtures, provenance
from app.flow import build_extract_messages
from app.schema import EvidenceSet
from slice.config import settings as load_settings

from pathlib import Path

NOTES = (Path(__file__).parent / "corpus" / "ds-notes.md").read_text(encoding="utf-8")

# A shortlist, not the full 22. Small and mid-size instruction-tuned models,
# because a 550B reasoning model is not going to be the fast one.
SHORTLIST = [
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
    "qwen/qwen3.8-27b:free",
    "z-ai/glm-5.2:free",
    "nvidia/nemotron-3.5-lightning:free",
    "liquid/lfm-2.5-2.6b:free",
    "poolside/laguna-xs-2.1:free",
    "poolside/laguna-s-2.1:free",
    "nex-agi/nex-n2.5-mini:free",
    "deepseek/deepseek-v4-flash-0731:free",
    "inclusionai/ling-3.0-flash-fin:free",
    "thinkingmachines/inkling-small:free",
]

GREEN, RED, YELLOW, DIM, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m")


def free_models(client: httpx.Client) -> list[str]:
    data = client.get("https://openrouter.ai/api/v1/models").json()["data"]
    return sorted(m["id"] for m in data if m["id"].endswith(":free"))


def trial(client: httpx.Client, model: str, key: str, max_tokens: int) -> dict:
    """One call. Returns what happened, never raises."""
    attempt = fixtures.MIRA_1
    messages = build_extract_messages(attempt, NOTES)
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "EvidenceSet", "strict": True,
                            "schema": EvidenceSet.model_json_schema()},
        },
    }
    started = time.time()
    try:
        r = client.post("https://openrouter.ai/api/v1/chat/completions",
                        json=body, headers={"Authorization": f"Bearer {key}"},
                        timeout=90.0)
    except Exception as e:
        return {"ok": False, "why": type(e).__name__, "secs": time.time() - started}
    secs = time.time() - started

    if r.status_code != 200:
        return {"ok": False, "why": f"HTTP {r.status_code}", "secs": secs}
    try:
        text = r.json()["choices"][0]["message"]["content"]
        parsed = EvidenceSet.model_validate_json(_strip_fence(text))
    except Exception as e:
        return {"ok": False, "why": f"parse: {type(e).__name__}", "secs": secs}

    sources = {f"{attempt['assignment_id']}#response": attempt["submission"],
               "course_notes": NOTES}
    checked = provenance.check_evidence(parsed.items, sources)
    good = sum(1 for c in checked if c.supported)
    return {"ok": True, "secs": secs, "rows": len(checked), "verbatim": good}


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return text.strip()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--trials", type=int, default=2)
    p.add_argument("--all", action="store_true")
    args = p.parse_args()

    settings = load_settings()
    if not settings.api_key:
        print(f"{RED}No OPENROUTER_API_KEY in .env{RESET}")
        return

    with httpx.Client() as client:
        models = free_models(client) if args.all else SHORTLIST
        print(f"{BOLD}{len(models)} free models, {args.trials} trials each{RESET}")
        print(f"{DIM}extraction prompt, Mira's first submission, temperature 0{RESET}\n")
        print(f"{'model':<46} {'parse':<7} {'secs':<7} verbatim")
        print("-" * 74)

        results = []
        for model in models:
            runs = [trial(client, model, settings.api_key, settings.max_tokens)
                    for _ in range(args.trials)]
            ok = [r for r in runs if r["ok"]]
            parse = f"{len(ok)}/{len(runs)}"

            if not ok:
                why = runs[0]["why"][:28]
                print(f"{model:<46} {RED}{parse:<7}{RESET} {DIM}{why}{RESET}")
                continue

            secs = statistics.median(r["secs"] for r in ok)
            rows = statistics.median(r["rows"] for r in ok)
            verb = statistics.median(r["verbatim"] for r in ok)
            clean = verb == rows and len(ok) == len(runs)
            colour = GREEN if clean and secs < 8 else (YELLOW if clean else RED)
            print(f"{model:<46} {colour}{parse:<7}{RESET} {secs:<7.1f} "
                  f"{colour}{int(verb)}/{int(rows)}{RESET}")
            results.append((model, len(ok) / len(runs), secs, verb / rows if rows else 0))

        print()
        usable = [r for r in results if r[1] == 1.0 and r[3] == 1.0]
        if not usable:
            print(f"{YELLOW}Nothing scored perfectly. Widen with --all, or raise "
                  f"SLICE_MAX_TOKENS if failures say 'parse'.{RESET}")
            return
        usable.sort(key=lambda r: r[2])
        best = usable[0]
        print(f"{BOLD}Fastest that held the contract:{RESET} {GREEN}{best[0]}{RESET}"
              f" — {best[2]:.1f}s, every passage verbatim")
        print(f"{DIM}Put it in .env as SLICE_MODEL, and pick a different provider "
              f"family for SLICE_FALLBACK_MODEL. Re-run with --trials 5 before "
              f"trusting it.{RESET}")


if __name__ == "__main__":
    main()
