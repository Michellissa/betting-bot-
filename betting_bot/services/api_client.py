"""Base HTTP API client with retry, rate limiting, and caching."""

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from betting_bot.core.exceptions import APIError


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""

    requests_per_minute: int = 10
    requests_per_day: int = 1000
    last_reset: float = field(default_factory=time.time)
    request_count: int = 0


class ResponseCache:
    """Simple file-based response cache."""

    def __init__(self, cache_dir: Path = Path("data/cache/api"), ttl: int = 3600) -> None:
        self.cache_dir = cache_dir
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, url: str, params: dict | None) -> str:
        key = url
        if params:
            key += json.dumps(params, sort_keys=True)
        return hashlib.md5(key.encode()).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, url: str, params: dict | None = None) -> dict | None:
        """Get cached response if valid."""
        cache_key = self._cache_key(url, params)
        cache_path = self._cache_path(cache_key)

        if not cache_path.exists():
            return None

        with open(cache_path) as f:
            data = json.load(f)

        if time.time() - data["timestamp"] > self.ttl:
            cache_path.unlink(missing_ok=True)
            return None

        return data["response"]

    def set(self, url: str, params: dict | None, response: dict) -> None:
        """Cache a response."""
        cache_key = self._cache_key(url, params)
        cache_path = self._cache_path(cache_key)

        with open(cache_path, "w") as f:
            json.dump({"timestamp": time.time(), "response": response}, f)

    def clear(self) -> None:
        """Clear all cached responses."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink(missing_ok=True)


class BaseAPIClient(ABC):
    """Base class for all API clients with built-in retry and rate limiting."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limit: RateLimitConfig | None = None,
        cache_enabled: bool = True,
        cache_ttl: int = 3600,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit = rate_limit or RateLimitConfig()
        self.cache = ResponseCache(ttl=cache_ttl) if cache_enabled else None
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(5)

    @property
    async def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._client

    @abstractmethod
    def _get_headers(self) -> dict[str, str]:
        """Return headers for API requests."""
        ...

    async def _check_rate_limit(self) -> None:
        """Enforce rate limiting."""
        now = time.time()
        elapsed = now - self.rate_limit.last_reset

        if elapsed >= 60:
            self.rate_limit.request_count = 0
            self.rate_limit.last_reset = now

        if self.rate_limit.request_count >= self.rate_limit.requests_per_minute:
            wait_time = 60 - elapsed
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
            self.rate_limit.request_count = 0
            self.rate_limit.last_reset = time.time()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        data: dict | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Make an HTTP request with retry and caching."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        if use_cache and self.cache and method.upper() == "GET":
            cached = self.cache.get(url, params)
            if cached is not None:
                return cached

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                await self._check_rate_limit()

                async with self._semaphore:
                    client = await self.client
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        json=data,
                        headers=self._get_headers(),
                    )

                self.rate_limit.request_count += 1

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    logger.warning(f"Rate limited (429), waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                result: dict = response.json()

                if use_cache and self.cache and method.upper() == "GET":
                    self.cache.set(url, params, result)

                return result

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code in (401, 403):
                    raise APIError(
                        f"Authentication failed for {self.__class__.__name__}",
                        status_code=e.response.status_code,
                    ) from e
                if e.response.status_code in (404,):
                    raise APIError(
                        f"Resource not found: {endpoint}",
                        status_code=404,
                    ) from e
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    wait = 2**attempt
                    logger.warning(f"Server error {e.response.status_code}, retrying in {wait}s")
                    await asyncio.sleep(wait)
                    continue
                raise APIError(
                    f"HTTP error from {self.__class__.__name__}: {e}",
                    status_code=e.response.status_code,
                ) from e

            except httpx.RequestError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait = 2**attempt
                    logger.warning(f"Request failed: {e}, retrying in {wait}s")
                    await asyncio.sleep(wait)
                    continue
                raise APIError(
                    f"Request failed after {self.max_retries} retries: {e}"
                ) from e

        raise APIError(f"Request failed after {self.max_retries} retries") from last_error

    async def get(
        self,
        endpoint: str,
        params: dict | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Make a GET request."""
        return await self._request("GET", endpoint, params=params, use_cache=use_cache)

    async def post(
        self,
        endpoint: str,
        data: dict | None = None,
    ) -> dict[str, Any]:
        """Make a POST request."""
        return await self._request("POST", endpoint, data=data, use_cache=False)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
