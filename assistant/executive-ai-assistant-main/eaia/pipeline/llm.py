"""
pipeline/llm.py — Shared LLM caller: 3-tier fallback + circuit breaker.

Fallback chain (configurable via NYX_LLM_FALLBACK env):
  1. Cohere command-r-plus
  2. OpenAI gpt-4o-mini
  3. Anthropic claude-3-haiku

Circuit breaker:
  After N consecutive failures on a provider, skip it for 60s.
  N is configurable via NYX_LLM_CIRCUIT_BREAKER (default 3).
"""
import os
import json
import time
import logging
import requests
from typing import Dict, Any

from eaia.config import NyxConfig

logger = logging.getLogger(__name__)

# ── Circuit Breaker State ─────────────────────────────────────────────────────
# Tracks consecutive failures per provider. When threshold hit, provider
# is skipped for 60s to avoid hammering a failing API.
_failure_counts: Dict[str, int] = {}
_circuit_open_until: Dict[str, float] = {}
CIRCUIT_COOLDOWN = 60  # seconds


def _is_circuit_open(provider: str) -> bool:
    """Check if a provider's circuit breaker is open (should skip)."""
    if provider in _circuit_open_until:
        if time.time() < _circuit_open_until[provider]:
            return True
        # Circuit cooldown expired — reset
        del _circuit_open_until[provider]
        _failure_counts[provider] = 0
    return False


def _record_failure(provider: str):
    """Record a failure and potentially open the circuit."""
    _failure_counts[provider] = _failure_counts.get(provider, 0) + 1
    if _failure_counts[provider] >= NyxConfig.LLM_CIRCUIT_BREAKER_THRESHOLD:
        _circuit_open_until[provider] = time.time() + CIRCUIT_COOLDOWN
        logger.warning(
            f"⚡ Circuit breaker OPEN for {provider}: "
            f"{_failure_counts[provider]} consecutive failures. "
            f"Skipping for {CIRCUIT_COOLDOWN}s."
        )


def _record_success(provider: str):
    """Reset failure count on success."""
    _failure_counts[provider] = 0
    if provider in _circuit_open_until:
        del _circuit_open_until[provider]


# ── Provider Implementations ──────────────────────────────────────────────────

def _call_cohere(prompt: str, timeout: int) -> Dict[str, Any]:
    """Call Cohere command-r-plus."""
    key = os.getenv("COHERE_API_KEY")
    if not key:
        raise ValueError("COHERE_API_KEY not set")

    r = requests.post(
        "https://api.cohere.com/v2/chat",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": "command-r-plus-08-2024",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"][0]["text"])


def _call_openai(prompt: str, timeout: int) -> Dict[str, Any]:
    """Call OpenAI gpt-4o-mini."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY not set")

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a JSON-only assistant. Return ONLY valid JSON, no markdown.",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


def _strip_json_fence(content: str) -> str:
    """Strip ```json ... ``` markdown fences some models wrap JSON in."""
    content = content.strip()
    if content.startswith("```"):
        # drop leading fence line (``` or ```json) and trailing fence
        content = content.split("```", 2)[1]
        if content.lstrip().lower().startswith("json"):
            content = content.lstrip()[4:]
    # some models still emit a trailing ``` if only one fence was captured
    if content.rstrip().endswith("```"):
        content = content.rstrip()[:-3]
    return content.strip()


def _call_openrouter(prompt: str, timeout: int) -> Dict[str, Any]:
    """Call OpenRouter (default model google/gemma-3-27b-it). Model via OPENROUTER_MODEL."""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise ValueError("OPENROUTER_API_KEY not set")

    model = os.getenv("OPENROUTER_MODEL", "google/gemma-3-27b-it")
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Return ONLY valid JSON, no markdown fences or explanation.\n\n"
                        + prompt
                    ),
                }
            ],
            "max_tokens": 4096,
        },
        timeout=timeout,
    )
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    return json.loads(_strip_json_fence(content))


def _call_anthropic(prompt: str, timeout: int) -> Dict[str, Any]:
    """Call Anthropic claude-3-haiku."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-3-haiku-20240307",
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": f"Return ONLY valid JSON, no markdown or explanation.\n\n{prompt}",
                }
            ],
        },
        timeout=timeout,
    )
    r.raise_for_status()
    content = r.json()["content"][0]["text"]
    # Anthropic may wrap JSON in markdown — strip it
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content.strip())


# ── Provider Registry ─────────────────────────────────────────────────────────

PROVIDERS = {
    "openrouter": _call_openrouter,
    "cohere": _call_cohere,
    "openai": _call_openai,
    "anthropic": _call_anthropic,
}


# ── Main Entry Point ─────────────────────────────────────────────────────────

def llm_json(prompt: str, timeout: int = 45) -> Dict[str, Any]:
    """
    Call LLM and get a JSON response with 3-tier fallback + circuit breaker.

    Fallback order: configurable via NyxConfig.LLM_FALLBACK_ORDER.
    Default: cohere → openai → anthropic.

    Circuit breaker: after N consecutive failures, skip provider for 60s.

    Args:
        prompt: Full prompt string. Should instruct the model to return JSON.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON dict from LLM response.

    Raises:
        RuntimeError: If all providers fail.
    """
    errors = []

    for provider_name in NyxConfig.LLM_FALLBACK_ORDER:
        provider_name = provider_name.strip()
        provider_fn = PROVIDERS.get(provider_name)
        if not provider_fn:
            continue

        # Check circuit breaker
        if _is_circuit_open(provider_name):
            logger.info(f"⚡ Skipping {provider_name} — circuit breaker open")
            continue

        try:
            start = time.time()
            result = provider_fn(prompt, timeout)
            elapsed = time.time() - start

            _record_success(provider_name)
            logger.info(f"✅ LLM response from {provider_name} in {elapsed:.1f}s")
            return result

        except Exception as e:
            _record_failure(provider_name)
            errors.append(f"{provider_name}: {e}")
            logger.warning(f"❌ {provider_name} failed: {e}")

    raise RuntimeError(
        f"All LLM providers failed. Errors: {'; '.join(errors)}. "
        f"Set COHERE_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY."
    )


# backward-compat aliases used throughout the codebase
_llm_json = llm_json
_cohere_json = llm_json
