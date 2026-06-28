"""User-Agent rotation utility.

Provides random user-agent strings. Uses fake-useragent if installed,
otherwise falls back to a curated list of modern browser UAs.
"""

from __future__ import annotations

import random

# Curated fallback list of modern browser user agents (updated June 2026)
_FALLBACK_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

_fake_ua = None
_fake_ua_attempted = False


def get_random_user_agent() -> str:
    """Return a random user-agent string.

    Attempts to use the ``fake-useragent`` library for more varied UAs.
    Falls back to a curated list if the library is unavailable.
    """
    global _fake_ua, _fake_ua_attempted

    if not _fake_ua_attempted:
        _fake_ua_attempted = True
        try:
            from fake_useragent import UserAgent
            _fake_ua = UserAgent(fallback=_FALLBACK_USER_AGENTS[0])
        except ImportError:
            _fake_ua = None

    if _fake_ua is not None:
        try:
            return _fake_ua.random
        except Exception:
            pass

    return random.choice(_FALLBACK_USER_AGENTS)
