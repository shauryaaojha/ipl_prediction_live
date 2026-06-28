"""Async HTTP client wrapper.

Provides a configured httpx.AsyncClient with:
- Retry logic (exponential backoff via tenacity)
- Rate limiting
- User-agent rotation
- Optional proxy rotation
- ETag / If-Modified-Since support
"""

from __future__ import annotations

import asyncio
import hashlib
import random
from typing import Any, Dict, Optional

import httpx
from loguru import logger
from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .user_agent import get_random_user_agent
from ..storage.cache_manager import CacheManager


class HttpClient:
    """Async HTTP client with retry, rate-limiting, and caching."""

    def __init__(
        self,
        max_retries: int = 3,
        request_delay: float = 1.5,
        request_delay_max: float = 3.5,
        timeout: float = 30.0,
        http2: bool = True,
        proxy_url: Optional[str] = None,
        cache: Optional[CacheManager] = None,
    ):
        self.max_retries = max_retries
        self.request_delay = request_delay
        self.request_delay_max = request_delay_max
        self.timeout = timeout
        self.cache = cache or CacheManager()

        transport_kwargs: Dict[str, Any] = {}
        if proxy_url:
            transport_kwargs["proxy"] = proxy_url

        self.client = httpx.AsyncClient(
            http2=http2,
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            follow_redirects=True,
            **transport_kwargs,
        )

    async def close(self):
        """Close the underlying httpx client."""
        await self.client.aclose()

    def _build_headers(self, extra_headers: Optional[Dict] = None) -> Dict[str, str]:
        headers = {
            "User-Agent": get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def _rate_limit(self):
        """Apply a randomized delay between requests."""
        delay = random.uniform(self.request_delay, self.request_delay_max)
        await asyncio.sleep(delay)

    async def get(
        self,
        url: str,
        use_cache: bool = True,
        max_cache_age_hours: int = 24,
        extra_headers: Optional[Dict] = None,
    ) -> httpx.Response:
        """Perform a GET request with retry, rate-limiting, and caching.

        Args:
            url: The URL to fetch.
            use_cache: Whether to use ETag / If-Modified-Since caching.
            max_cache_age_hours: Maximum cache age before re-fetching.
            extra_headers: Additional headers to include.

        Returns:
            httpx.Response object.

        Raises:
            httpx.HTTPStatusError: On non-retryable HTTP errors.
        """
        await self._rate_limit()

        headers = self._build_headers(extra_headers)

        # Add cache headers if available
        if use_cache:
            etag = self.cache.get_etag(url)
            if etag:
                headers["If-None-Match"] = etag
            last_mod = self.cache.get_last_modified(url)
            if last_mod:
                headers["If-Modified-Since"] = last_mod

        response = await self._fetch_with_retry(url, headers)

        # Update cache
        if use_cache and response.status_code == 200:
            self.cache.update(
                url=url,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
                response_hash=hashlib.md5(response.content).hexdigest(),
                status_code=response.status_code,
                content_length=len(response.content),
            )

        return response

    async def get_json(self, url: str, **kwargs) -> Any:
        """Fetch a URL and parse the response as JSON."""
        response = await self.get(url, **kwargs)
        response.raise_for_status()
        return response.json()

    async def get_text(self, url: str, **kwargs) -> str:
        """Fetch a URL and return the response text."""
        response = await self.get(url, **kwargs)
        response.raise_for_status()
        return response.text

    async def _fetch_with_retry(self, url: str, headers: Dict) -> httpx.Response:
        """Fetch with exponential backoff retry on transient errors."""
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.get(url, headers=headers)
                # Retry on server errors and rate limiting
                if response.status_code in (429, 500, 502, 503, 504):
                    logger.warning(
                        "HTTP {} for {} (attempt {}/{})",
                        response.status_code, url, attempt, self.max_retries,
                    )
                    if attempt < self.max_retries:
                        backoff = min(2 ** attempt + random.random(), 60)
                        await asyncio.sleep(backoff)
                        continue
                return response
            except (httpx.NetworkError, httpx.TimeoutException) as e:
                last_exception = e
                logger.warning(
                    "Network error for {} (attempt {}/{}): {}",
                    url, attempt, self.max_retries, e,
                )
                if attempt < self.max_retries:
                    backoff = min(2 ** attempt + random.random(), 60)
                    await asyncio.sleep(backoff)

        if last_exception:
            raise last_exception
        raise httpx.NetworkError(f"All {self.max_retries} retries exhausted for {url}")
