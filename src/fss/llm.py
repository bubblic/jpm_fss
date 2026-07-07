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


def default_client() -> AzureLLMClient | None:
    """The configured client, or None when the endpoint is not set."""
    if not os.getenv(ENDPOINT_ENV, "").strip():
        return None
    return AzureLLMClient()


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
