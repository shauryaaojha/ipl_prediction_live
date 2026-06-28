"""Proxy rotation utility.

Manages a pool of proxy URLs and rotates through them for each request.
Disabled by default — enable via config `scraping.proxy_rotation: true`
and provide proxy list in PROXY_LIST env var.
"""

from __future__ import annotations

import os
import random
from typing import List, Optional

from loguru import logger


class ProxyRotator:
    """Rotates through a pool of proxy URLs."""

    def __init__(self, proxy_list: Optional[List[str]] = None):
        if proxy_list is None:
            env_proxies = os.getenv("PROXY_LIST", "")
            proxy_list = [p.strip() for p in env_proxies.split(",") if p.strip()]

        self.proxies = proxy_list
        self._index = 0

        if self.proxies:
            logger.info("Proxy rotator initialized with {} proxies.", len(self.proxies))
        else:
            logger.info("No proxies configured — direct connections will be used.")

    @property
    def is_enabled(self) -> bool:
        return len(self.proxies) > 0

    def get_next(self) -> Optional[str]:
        """Get the next proxy URL in rotation."""
        if not self.proxies:
            return None
        proxy = self.proxies[self._index % len(self.proxies)]
        self._index += 1
        return proxy

    def get_random(self) -> Optional[str]:
        """Get a random proxy URL from the pool."""
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    def remove(self, proxy: str) -> None:
        """Remove a proxy from the pool (e.g., if it's dead)."""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            logger.warning("Removed dead proxy: {}. {} remaining.", proxy, len(self.proxies))

    def add(self, proxy: str) -> None:
        """Add a proxy to the pool."""
        if proxy not in self.proxies:
            self.proxies.append(proxy)
