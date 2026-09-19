"""
One place that reads configuration. Nowhere else calls os.environ.

Scattered getenv calls are how a project ends up with three different defaults
for the same setting and no idea which one is live. Everything comes from .env,
loaded once, with the defaults visible here rather than buried at call sites.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_env(path: str | Path = ".env") -> bool:
    """Read .env into the environment. Real environment variables win, so a
    Codespaces secret or an exported value can override the file."""
    try:
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
        return True
    except FileNotFoundError:
        return False


@dataclass(frozen=True)
class Settings:
    api_key: str
    groq_key: str
    """Groq, if set, is the primary provider. Added by us, not the kit.

    Two reasons, both measured rather than assumed. The event's OpenRouter keys
    are free-tier and shared: 50 free-model requests a day across every team, so
    a busy room returns 429 to everybody at once. And Groq's inference is an
    order of magnitude faster on this workload - 0.9s against 15-20s on the same
    prompt - which turns a 75-second encounter into about four.

    OpenRouter stays as the fallback, which is what a fallback is for: a
    different provider family, so one outage is not both.
    """
    model: str
    fallback_model: str
    escalation_model: str
    max_tokens: int              # per request
    max_tokens_per_run: int      # the run-level fence
    max_attempts_per_step: int
    expert_timeout_minutes: int
    langfuse_public: str
    langfuse_secret: str
    langfuse_host: str

    @property
    def tracing_enabled(self) -> bool:
        return bool(self.langfuse_public and self.langfuse_secret)


def settings(reload: bool = True) -> Settings:
    if reload:
        load_env()
    g = os.environ.get
    return Settings(
        api_key               = g("OPENROUTER_API_KEY", "").strip(),
        groq_key              = g("GROQ_API_KEY", "").strip(),
        model                 = g("SLICE_MODEL", "qwen/qwen3.8-27b").strip(),
        fallback_model        = g("SLICE_FALLBACK_MODEL",
                                  "mistralai/mistral-small-3.2-24b-instruct").strip(),
        escalation_model      = g("SLICE_ESCALATION_MODEL", "anthropic/claude-haiku-4.5").strip(),
        max_tokens            = int(g("SLICE_MAX_TOKENS", "1200")),
        max_tokens_per_run    = int(g("SLICE_MAX_TOKENS_PER_RUN", "250000")),
        max_attempts_per_step = int(g("SLICE_MAX_ATTEMPTS_PER_STEP", "3")),
        expert_timeout_minutes= int(g("SLICE_EXPERT_TIMEOUT_MINUTES", "45")),
        langfuse_public       = g("LANGFUSE_PUBLIC_KEY", "").strip(),
        langfuse_secret       = g("LANGFUSE_SECRET_KEY", "").strip(),
        langfuse_host         = g("LANGFUSE_HOST", "https://cloud.langfuse.com").strip(),
    )
