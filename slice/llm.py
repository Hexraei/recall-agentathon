"""
The one place a model is ever called.

Every architectural concern that touches a model call is enforced HERE, in one
function, rather than sprinkled across the agents:

    typed contracts   the reply is parsed into your schema, or repaired once
    bounded loops     the token fence is checked before the request goes out
    degradation       a named fallback model, a different provider family
    observability     one span per call, no-ops if tracing is not configured
    cost classifying  a 402 means one of two very different things

That last one is worth reading twice. OpenRouter refuses a request BEFORE
running it if the worst case exceeds the remaining balance - so a 402 arrives
with nothing spent. But there are two reasons it can arrive, and they need
opposite responses under pressure:

    your TEAM's key cap is spent    -> routine, go and get a top-up
    the SHARED account is empty     -> every team is about to stop, tell an
                                        organiser immediately

A student cannot tell those apart from a raw error, so we do it for them.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Type

import httpx
from pydantic import BaseModel, ValidationError

from .budget import Budget
from .config import Settings

API = "https://openrouter.ai/api/v1"
GROQ_API = "https://api.groq.com/openai/v1"

# Models Groq serves. Anything not here is assumed to be an OpenRouter id, so
# the two providers can be mixed in one attempt chain without a prefix scheme.
# Measured on this repo's extraction prompt, 3 trials each, 18 Sep 2026:
#   qwen/qwen3.8-27b      0.89s   3/3 parsed, every passage verbatim
#   openai/gpt-oss-20b    1.67s   3/3
#   openai/gpt-oss-120b   2.35s   3/3
# against inclusionai/ling-3.0-flash on OpenRouter at 15-20s.
GROQ_MODELS = {
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-safeguard-20b",
    "groq/compound",
    "groq/compound-mini",
    "allam-2-7b",
}


MAX_RATE_LIMIT_WAIT = 20.0
"""Longest we will sit on a 429 before giving up on that model.

Groq's free tier is 8,000 tokens per minute, and an encounter costs ~4,500 - so
two runs back to back hit the ceiling and the API replies "try again in 11.6s".
That is a queue, not an outage, and waiting it out is right. Beyond twenty
seconds it is no longer a queue and the fallback is the better answer.
"""


def _retry_after(r: httpx.Response) -> float | None:
    """How long the provider says to wait, in seconds, or None if it did not say.

    Honours the standard Retry-After header, then Groq's own reset headers,
    then the wait quoted in the error message itself.
    """
    header = r.headers.get("retry-after")
    if header:
        try:
            return float(header)
        except ValueError:
            pass
    for name in ("x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
        raw = r.headers.get(name)
        if raw:
            parsed = _duration(raw)
            if parsed is not None:
                return parsed
    match = re.search(r"try again in ([\d.]+)s", r.text)
    return float(match.group(1)) if match else None


def _duration(raw: str) -> float | None:
    """Parse Groq's duration strings: '11.5s', '105ms', '1m26.4s'."""
    match = re.fullmatch(r"(?:(\d+)m)?([\d.]+)(ms|s)?", raw.strip())
    if not match:
        return None
    minutes, value, unit = match.groups()
    seconds = float(value) / 1000 if unit == "ms" else float(value)
    return seconds + (int(minutes) * 60 if minutes else 0)


def _route(model: str, settings: Settings) -> tuple[str, str, str]:
    """Where does this model live? Returns (base_url, api_key, provider).

    Groq only if we have a key for it; otherwise everything falls to
    OpenRouter, which is also the path when GROQ_API_KEY is unset - so a
    checkout with no Groq key behaves exactly as the kit shipped.
    """
    if model in GROQ_MODELS and settings.groq_key:
        return GROQ_API, settings.groq_key, "groq"
    return API, settings.api_key, "openrouter"


class ModelError(RuntimeError):
    """Base for everything that can go wrong at the model boundary."""


class CapExhausted(ModelError):
    """This team's key has spent its cap. One team affected."""


class PoolExhausted(ModelError):
    """The shared account is out of credit. EVERY team is affected."""


class SchemaFailure(ModelError):
    """The model would not produce the agreed shape, even after a repair pass."""


class Truncated(ModelError):
    """The reply was cut off at max_tokens, mid-answer.

    This is NOT the model failing to follow instructions, and telling the two
    apart matters: a repair pass on a truncated reply hits the same ceiling and
    fails identically. We found this the hard way - a model that looked
    "intermittently disobedient" was simply verbose, and our max_tokens was too
    low. Verbosity varies run to run, so the failure looked random.
    """


def _classify_402(body: dict) -> ModelError:
    """Read the error rather than guessing at it.

    Verified 3 Sep 2026: a key-cap rejection carries
    metadata.limit_source == "openrouter_key_limit". The account-level string
    is NOT verified - we have never run the pool dry - so anything that is not
    a key limit is treated as the more serious case. Erring toward "tell an
    organiser" is the right bias: a false alarm costs a conversation, a missed
    one costs the event.
    """
    err = (body or {}).get("error", {}) or {}
    src = ((err.get("metadata") or {}).get("limit_source") or "").lower()
    msg = err.get("message", "") or json.dumps(body)[:300]
    if "key" in src:
        return CapExhausted(
            "Your team's API key has reached its spending cap.\n"
            "  -> Reduce SLICE_MAX_TOKENS, or ask the key desk for a top-up.\n"
            f"  (provider said: {msg})")
    return PoolExhausted(
        "The SHARED account is out of credit - this affects every team, not "
        "just yours.\n  -> Tell an organiser now. Do not wait.\n"
        f"  (provider said: {msg})")


class _Span:
    """Tracing that costs nothing when it is not configured.

    If Langfuse keys are absent this is an empty context manager, so no team is
    ever blocked at hour zero by an observability signup they have not done.
    """

    def __init__(self, s: Settings, name: str, meta: dict):
        self.enabled, self.name, self.meta = s.tracing_enabled, name, meta
        self._span = None

    def __enter__(self):
        if self.enabled:
            try:
                from langfuse import Langfuse  # imported lazily and optionally
                self._client = Langfuse()
                self._span = self._client.trace(name=self.name, metadata=self.meta)
            except Exception:
                self._span = None       # tracing must never break the run
        return self

    def record(self, **kw):
        if self._span is not None:
            try:
                self._span.update(**kw)
            except Exception:
                pass

    def __exit__(self, *exc):
        return False


def complete(
    *,
    settings: Settings,
    budget: Budget,
    messages: list[dict],
    schema: Type[BaseModel] | None = None,
    model: str | None = None,
    step: str = "call",
    timeout: float = 120.0,
) -> Any:
    """Call a model. Returns a parsed `schema` instance, or raw text if no
    schema was asked for.

    Raises CapExhausted / PoolExhausted / SchemaFailure / BudgetExceeded - all
    of which the runner handles explicitly. Nothing here raises a bare
    HTTPError into caller code.
    """
    budget.check_tokens()                       # refuse to start, not to finish

    primary = model or settings.model
    attempts: list[tuple[str, str]] = [(primary, "primary")]
    if settings.fallback_model and settings.fallback_model != primary:
        attempts.append((settings.fallback_model, "fallback"))

    last_text = ""
    waited = False
    with _Span(settings, f"llm:{step}", {"model": primary, "step": step}) as span:
        i = 0
        while i < len(attempts):
            mid, role = attempts[i]
            i += 1
            body = {
                "model": mid,
                "max_tokens": settings.max_tokens,
                "temperature": 0,
                "messages": messages,
            }
            if schema is not None:
                # Groq honours a real JSON schema, which is why it parsed 3/3
                # on every model tested. OpenRouter's json_object is looser and
                # leans on the repair pass below.
                if mid in GROQ_MODELS and settings.groq_key:
                    body["response_format"] = {
                        "type": "json_schema",
                        "json_schema": {"name": schema.__name__,
                                        "schema": schema.model_json_schema()},
                    }
                else:
                    body["response_format"] = {"type": "json_object"}

            base, key, provider = _route(mid, settings)
            t0 = time.time()
            try:
                r = httpx.post(f"{base}/chat/completions", json=body, timeout=timeout,
                               headers={"Authorization": f"Bearer {key}"})
            except httpx.RequestError as e:
                if role == "fallback":
                    raise ModelError(
                        f"Both models unreachable ({e}). Run "
                        "`python scripts/doctor.py` - this is usually the network "
                        "or a provider outage, not your code.") from e
                continue                       # network hiccup: try the fallback

            if r.status_code == 402:
                raise _classify_402(_safe_json(r))     # never worth a retry

            # A 429 from a token-per-minute limit is not an outage - it is a
            # queue, and it tells you how long the queue is. Falling straight
            # through to the fallback wastes that, and on a single-provider
            # setup the fallback is behind the SAME limit, so both fail and the
            # run dies on something that would have cleared in ten seconds.
            #
            # Wait once, if the wait is short enough to be worth it. Anything
            # longer is a real outage and should fall back instead.
            if r.status_code == 429 and not waited:
                delay = _retry_after(r)
                if delay is not None and delay <= MAX_RATE_LIMIT_WAIT:
                    span.record(output={"model": mid, "rate_limited": True,
                                        "waited": delay})
                    time.sleep(delay + 0.25)
                    waited = True
                    i -= 1                              # try this model again
                    continue

            # A 400 with this specific code is Groq's own schema-enforced
            # generation running out of room before it could produce valid
            # JSON - functionally the same failure as finish_reason == "length"
            # below, just reported before a 200 rather than inside one. Found
            # live: a genuinely all-strengths report (nothing to trim) hit this
            # intermittently. Retrying the SAME model changes nothing since it
            # hits the same ceiling; the fallback is a different model and may
            # simply be terser, so it gets the same treatment as a real 4xx/5xx.
            transient_400 = (r.status_code == 400
                             and "json_validate_failed" in r.text)
            if (r.status_code in (429, 500, 502, 503) or transient_400) \
                    and role == "primary":
                span.record(output={"model": mid, "transient_400": transient_400})
                continue                                # transient: fall back
            if r.status_code != 200:
                raise ModelError(f"{mid} returned HTTP {r.status_code}: {r.text[:300]}")

            data = r.json()
            used = (data.get("usage") or {}).get("total_tokens", 0)
            budget.record_tokens(used)
            choice = data["choices"][0]
            last_text = choice["message"]["content"] or ""

            # Cut off mid-answer? Retrying the same model changes nothing - it
            # hits the same ceiling. Fall back instead: the fallback is a
            # different model and may simply be terser.
            if choice.get("finish_reason") == "length":
                span.record(output={"model": mid, "truncated": True, "tokens": used})
                if role == "primary" and len(attempts) > 1:
                    continue
                raise Truncated(
                    f"{mid} was cut off at max_tokens ({settings.max_tokens}) "
                    "before finishing. This is not a prompt problem.\n"
                    "  -> Raise SLICE_MAX_TOKENS, or ask the agent for a shorter "
                    "answer (fewer items, shorter fields).")
            span.record(output={"model": mid, "role": role, "provider": provider,
                                "tokens": used,
                                "seconds": round(time.time() - t0, 2)})

            if schema is None:
                return last_text

            parsed = _parse(last_text, schema)
            if parsed is not None:
                return parsed

            # One repair pass. Show the model its own output and the error -
            # a second identical request usually fails identically.
            repaired = _repair(settings, budget, messages, last_text, schema, mid, timeout)
            if repaired is not None:
                return repaired
            if role == "fallback":
                break
            # primary could not hold the contract; the fallback might

    raise SchemaFailure(
        f"No model produced valid {schema.__name__ if schema else 'output'} "
        f"after a repair pass. Last reply began: {last_text[:200]!r}")


def _safe_json(r: httpx.Response) -> dict:
    try:
        return r.json()
    except Exception:
        return {"error": {"message": r.text[:300]}}


def _strip_fence(text: str) -> str:
    """Models wrap JSON in markdown fences even when told not to. That is a
    formatting habit, not a failure to follow the contract, so we forgive it
    here rather than burning a repair pass on it."""
    t = (text or "").strip()
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) > 1:
            t = parts[1]
            if t.lstrip().lower().startswith("json"):
                t = t.lstrip()[4:]
    return t.strip()


def _parse(text: str, schema: Type[BaseModel]):
    try:
        return schema.model_validate_json(_strip_fence(text))
    except (ValidationError, ValueError):
        return None


def _repair(settings, budget, messages, bad_text, schema, mid, timeout):
    budget.check_tokens()
    try:
        schema.model_validate_json(_strip_fence(bad_text))
    except Exception as e:
        why = str(e)[:600]
    else:
        return None
    fix = messages + [
        {"role": "assistant", "content": bad_text[:2000]},
        {"role": "user", "content":
            "That did not match the required schema.\n\n"
            f"Error:\n{why}\n\n"
            f"Required JSON schema:\n{json.dumps(schema.model_json_schema())}\n\n"
            "Reply with the corrected JSON object and nothing else."},
    ]
    base, key, _ = _route(mid, settings)
    try:
        r = httpx.post(f"{base}/chat/completions", timeout=timeout,
                       headers={"Authorization": f"Bearer {key}"},
                       json={"model": mid, "max_tokens": settings.max_tokens,
                             "temperature": 0, "messages": fix,
                             "response_format": {"type": "json_object"}})
    except httpx.RequestError:
        return None
    if r.status_code == 402:
        raise _classify_402(_safe_json(r))
    if r.status_code != 200:
        return None
    data = r.json()
    budget.record_tokens((data.get("usage") or {}).get("total_tokens", 0))
    return _parse(data["choices"][0]["message"]["content"] or "", schema)
