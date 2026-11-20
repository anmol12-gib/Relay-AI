"""LiteLLM gateway: exact-prompt caching, per-key failover, honest metadata."""
import asyncio
import logging
import re
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
SIMULATED_STATUSES = {429, 500, 502, 503}


class AllProvidersUnavailable(Exception):
    pass


class ProviderRequestFailed(Exception):
    pass


def parse_simulation(header: str | None) -> dict[str, int]:
    if not header:
        return {}
    results = {}
    for part in header.split(","):
        match = re.fullmatch(r"\s*(key_[1-9]\d*|\*)=(429|500|502|503)\s*", part)
        if match:
            results[match.group(1)] = int(match.group(2))
    return results


def is_retryable(error: Exception) -> bool:
    status = getattr(error, "status_code", None) or getattr(error, "http_status", None)
    if isinstance(status, int) and (status == 429 or 500 <= status <= 599):
        return True
    name = type(error).__name__.lower()
    message = str(error).lower()
    return (any(v in name for v in ("ratelimit", "serviceunavailable", "apiconnection", "timeout", "internalserver"))
            or any(v in message for v in ("quota exceeded", "quota exhausted", "resource_exhausted", "rate limit", "rate_limit")))


@dataclass
class LLMAnswer:
    reply: str
    model: str
    input_tokens: int
    output_tokens: int
    key_id: str | None
    fallback_attempts: int
    source: str


class LiteLLMGateway:
    def __init__(self, keys: tuple[str, ...], model: str, timeout: int = 45):
        self.keys = keys
        self.model = model
        self.timeout = timeout
        # Imported lazily to allow deterministic tests without live credentials.
        import litellm
        from litellm.caching.caching import Cache
        litellm.suppress_debug_info = True
        litellm.drop_params = True
        # LiteLLM's built-in cache, shared across all keys for the same model+messages.
        litellm.cache = Cache(type="local")
        self.litellm = litellm

    def _complete_one(self, key: str, messages: list[dict], caching: bool):
        return self.litellm.completion(
            model=self.model,
            messages=messages,
            api_key=key,
            caching=caching,
            timeout=self.timeout,
            temperature=0.7,
        )

    async def complete(self, messages: list[dict], simulation: dict[str, int] | None = None) -> LLMAnswer:
        simulation = simulation or {}
        # Simulated failures must exercise the key pool, not be hidden by a previous cache hit.
        caching = not bool(simulation)
        failures = 0
        for index, key in enumerate(self.keys, start=1):
            key_id = f"key_{index}"
            if key_id in simulation or "*" in simulation:
                failures += 1
                logger.info("Simulated provider failure for %s", key_id)
                continue
            try:
                response = await asyncio.to_thread(self._complete_one, key, messages, caching)
                hidden = getattr(response, "_hidden_params", {}) or {}
                # LiteLLM exposes the cache-hit flag on the returned response.
                hit = bool(hidden.get("cache_hit"))
                content = response.choices[0].message.content
                if not isinstance(content, str) or not content.strip():
                    raise ProviderRequestFailed("Provider returned an empty response")
                usage = getattr(response, "usage", None)
                return LLMAnswer(
                    reply=content,
                    model=self.model,
                    input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
                    output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
                    key_id=None if hit else key_id,
                    fallback_attempts=0 if hit else failures,
                    source="LLM_CACHE" if hit else "LIVE_INFERENCE",
                )
            except Exception as exc:
                if not is_retryable(exc):
                    logger.warning("Provider request error on %s (%s)", key_id, type(exc).__name__)
                    # Never expose provider details or API secrets.
                    raise ProviderRequestFailed() from None
                failures += 1
                logger.warning("Retryable provider failure on %s (%s)", key_id, type(exc).__name__)
        raise AllProvidersUnavailable()
