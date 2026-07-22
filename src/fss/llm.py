"""LLM client adopting the calling logic of previous_llm_extractor.

The client mirrors the user's ``AzureLLMClient``: payloads are posted as
``{"message": ..., "body": {"prompt": ..., "parameters": ..., "reasoning":
...}}`` to the endpoint named by ``AZURE_DEEPSEEK_ENDPOINT`` (``.env``
supported), with patient retry on throttling/5xx and tolerant JSON
extraction (the gateway wraps responses as ``data.response``, sometimes as
free text with an embedded JSON object).

Two policies wrap the raw client for FSS use:
  - availability is environment-gated (``default_client()`` returns None
    when no endpoint is configured, and every LLM-assisted stage degrades
    to its deterministic behavior with a note);
  - LLM readings that feed the extraction gate use median voting across
    repeated runs (the user's hallucination-control method): a value is
    kept only when it equals the median of ``n_runs`` samples.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from statistics import median_low
from typing import Any, Protocol, runtime_checkable

try:  # mirror the user's dotenv loading; optional at runtime
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

ENDPOINT_ENV = "AZURE_DEEPSEEK_ENDPOINT"
DEEPSEEK_KEY_ENV = "DEEPSEEK_API_KEY"
DEEPSEEK_MODEL_ENV = "DEEPSEEK_TEXT_MODEL"
DEEPSEEK_BASE_ENV = "DEEPSEEK_API_BASE_URL"


@runtime_checkable
class LLMClient(Protocol):
    """Structural interface, identical to previous_llm_extractor."""

    def ask_json(
        self,
        message: str,
        prompt: str,
        parameters: dict[str, Any],
        reasoning: bool = True,
    ) -> dict[str, Any]: ...

    def ask_text(
        self,
        message: str,
        prompt: str,
        parameters: dict[str, Any],
        reasoning: bool = True,
    ) -> str: ...


class AzureLLMClient:
    """Azure-gateway LLM client (the user's calling logic)."""

    def __init__(
        self,
        endpoint: str | None = None,
        timeout_seconds: int = 120,
        max_attempts: int = 20,
    ) -> None:
        self.endpoint = (endpoint or os.getenv(ENDPOINT_ENV, "")).strip()
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        if not self.endpoint:
            raise ValueError(f"Missing Azure config. Set {ENDPOINT_ENV}.")

    def ask_json(
        self,
        message: str,
        prompt: str,
        parameters: dict[str, Any],
        reasoning: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "message": message,
            "body": {"prompt": prompt, "parameters": parameters, "reasoning": reasoning},
        }
        return extract_json(self._post_json(payload))

    def ask_text(
        self,
        message: str,
        prompt: str,
        parameters: dict[str, Any],
        reasoning: bool = True,
    ) -> str:
        response = self.ask_json(message, prompt, parameters, reasoning)
        if isinstance(response, dict) and "raw_response" in response:
            return str(response["raw_response"])
        return json.dumps(response, ensure_ascii=False)

    def _post_json(self, payload: dict[str, Any]) -> str:
        data = json.dumps(payload).encode("utf-8")
        backoff_seconds = 1.0
        last_exc: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            request = urllib.request.Request(
                self.endpoint,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as resp:
                    return resp.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                last_exc = exc
                if exc.code not in (429, 500, 502, 503, 504):
                    raise
            except Exception as exc:  # timeouts, transport errors
                last_exc = exc
            if attempt == self.max_attempts:
                break
            time.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 10.0)
        raise RuntimeError(f"Azure API request failed: {last_exc}") from last_exc


class DeepSeekClient:
    """Direct DeepSeek API client (OpenAI-compatible chat completions).

    Mirrors the user's configuration: ``DEEPSEEK_API_KEY``,
    ``DEEPSEEK_TEXT_MODEL`` (default ``deepseek-v4-flash``), and
    ``DEEPSEEK_API_BASE_URL`` (default ``https://api.deepseek.com``) with
    ``/chat/completions`` appended. Exposes the same ``ask_json``/
    ``ask_text`` surface as the gateway client so every calling site is
    unchanged; the retry/backoff and tolerant JSON unwrapping policies are
    identical.
    """

    def __init__(
        self,
        timeout_seconds: int = 120,
        max_attempts: int = 20,
    ) -> None:
        self.model_name = os.getenv(DEEPSEEK_MODEL_ENV, "deepseek-v4-flash")
        self.api_key = os.getenv(DEEPSEEK_KEY_ENV, "").strip()
        self.endpoint = (
            os.getenv(DEEPSEEK_BASE_ENV, "https://api.deepseek.com").rstrip("/")
            + "/chat/completions"
        )
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        if not self.api_key:
            raise ValueError(f"Missing DeepSeek config. Set {DEEPSEEK_KEY_ENV}.")

    def ask_json(
        self,
        message: str,
        prompt: str,
        parameters: dict[str, Any],
        reasoning: bool = True,
    ) -> dict[str, Any]:
        content = self.ask_text(message, prompt, parameters, reasoning)
        try:
            loaded = json.loads(content)
            if isinstance(loaded, dict):
                return loaded
        except json.JSONDecodeError:
            pass
        embedded = extract_json_from_text(content)
        if embedded is not None:
            return embedded
        return {"raw_response": content}

    def ask_text(
        self,
        message: str,
        prompt: str,
        parameters: dict[str, Any],
        reasoning: bool = True,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            **(parameters or {}),
        }
        raw = self._post_json(payload)
        try:
            envelope = json.loads(raw)
            return str(envelope["choices"][0]["message"]["content"])
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"DeepSeek response shape unexpected: {exc}") from exc

    def _post_json(self, payload: dict[str, Any]) -> str:
        data = json.dumps(payload).encode("utf-8")
        backoff_seconds = 1.0
        last_exc: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            request = urllib.request.Request(
                self.endpoint,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as resp:
                    return resp.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                last_exc = exc
                if exc.code not in (429, 500, 502, 503, 504):
                    raise
            except Exception as exc:  # timeouts, transport errors
                last_exc = exc
            if attempt == self.max_attempts:
                break
            time.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 10.0)
        raise RuntimeError(f"DeepSeek API request failed: {last_exc}") from last_exc


def extract_json(response_text: str) -> dict[str, Any]:
    """Tolerant response unwrapping, as in the user's client."""
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"API did not return JSON: {exc}") from exc
    if isinstance(payload, dict) and "data" in payload:
        data = payload["data"]
        if isinstance(data, dict) and "response" in data:
            inner = data["response"]
            if isinstance(inner, str):
                try:
                    return json.loads(inner)
                except json.JSONDecodeError:
                    embedded = extract_json_from_text(inner)
                    if embedded is not None:
                        return embedded
                    return {"raw_response": inner}
        if isinstance(data, dict):
            return data
    if isinstance(payload, dict):
        return payload
    raise ValueError("Unexpected API response shape.")


def extract_json_from_text(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        loaded = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def default_client() -> "DeepSeekClient | AzureLLMClient | None":
    """The configured client, or None when nothing is set.

    The direct DeepSeek API key wins when present; the Azure gateway
    endpoint remains as a fallback path.
    """
    if os.getenv(DEEPSEEK_KEY_ENV, "").strip():
        return DeepSeekClient()
    if os.getenv(ENDPOINT_ENV, "").strip():
        return AzureLLMClient()
    return None


@dataclass(frozen=True)
class VotedValue:
    value: Decimal | None
    agreement: int  # how many runs matched the median
    runs: int


def median_vote(samples: list[Decimal | None], runs: int) -> VotedValue:
    """The user's hallucination rule: keep the median across repeated runs.

    None (the LLM abstained) participates: a value is returned only when a
    numeric median exists and at least half the runs agree with it exactly.
    """
    numeric = [s for s in samples if s is not None]
    if not numeric:
        return VotedValue(None, samples.count(None), runs)
    chosen = median_low(sorted(numeric))
    agreement = sum(1 for s in samples if s == chosen)
    if agreement * 2 < runs:
        return VotedValue(None, agreement, runs)
    return VotedValue(chosen, agreement, runs)
