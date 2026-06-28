"""Configuration manager.

Loads and merges YAML config files with environment variables using
pydantic-settings.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from loguru import logger


def _find_project_root() -> Path:
    """Find the project root by looking for config/ directory."""
    current = Path(__file__).resolve().parent.parent.parent  # src/core -> src -> project_root
    if (current / "config").is_dir():
        return current
    # Fallback: cwd
    cwd = Path.cwd()
    if (cwd / "config").is_dir():
        return cwd
    return current


def _resolve_env_vars(value: str) -> str:
    """Resolve ${VAR:default} placeholders in string values."""
    import re

    def replacer(match):
        var_name = match.group(1)
        default = match.group(3) if match.group(3) is not None else ""
        return os.getenv(var_name, default)

    return re.sub(r"\$\{([^:}]+)(:([^}]*))?\}", replacer, value)


def _deep_resolve(obj: Any) -> Any:
    """Recursively resolve environment variable placeholders in config."""
    if isinstance(obj, str):
        return _resolve_env_vars(obj)
    elif isinstance(obj, dict):
        return {k: _deep_resolve(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_deep_resolve(item) for item in obj]
    return obj


def load_yaml(filepath: Path) -> Dict[str, Any]:
    """Load a YAML file and resolve env var placeholders."""
    if not filepath.exists():
        logger.warning("Config file not found: {}", filepath)
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return _deep_resolve(raw)


def load_config(config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load all configuration files and merge them.

    Loads:
    1. config/scraper.yaml — main app config
    2. config/sources.yaml — URL templates and selectors
    3. config/logging.yaml — logging config
    4. .env file (via python-dotenv if available)

    Returns:
        Merged configuration dictionary.
    """
    if config_dir is None:
        config_dir = _find_project_root() / "config"

    # Try loading .env file
    try:
        from dotenv import load_dotenv
        env_path = config_dir.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logger.info("Loaded .env from {}", env_path)
    except ImportError:
        pass

    # Load YAML configs
    scraper_config = load_yaml(config_dir / "scraper.yaml")
    sources_config = load_yaml(config_dir / "sources.yaml")
    logging_config = load_yaml(config_dir / "logging.yaml")

    # Merge into single config dict
    config = {
        **scraper_config.get("app", {}),
        **scraper_config.get("scraping", {}),
        "scheduling": scraper_config.get("scheduling", {}),
        "sources": scraper_config.get("sources", {}),
        "database": scraper_config.get("database", {}),
        "storage": scraper_config.get("storage", {}),
        "features": scraper_config.get("features", {}),
        "sources_config": sources_config,
        "logging": logging_config,
    }

    logger.info(
        "Configuration loaded — Environment: {}, Data path: {}",
        config.get("environment", "unknown"),
        config.get("storage", {}).get("data_path", "unknown"),
    )

    return config


def setup_logging(config: Dict[str, Any]) -> None:
    """Configure loguru from the logging configuration."""
    from loguru import logger as _logger
    import sys

    logging_config = config.get("logging", {})
    log_config = logging_config.get("logging", logging_config)

    # Remove default handler
    _logger.remove()

    # Add console handler
    level = log_config.get("level", os.getenv("LOG_LEVEL", "INFO"))
    fmt = log_config.get("format", "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}")
    _logger.add(sys.stderr, level=level, format=fmt, colorize=log_config.get("colorize", True))

    # Add file handlers
    handlers = log_config.get("handlers", [])
    storage = config.get("storage", {})
    data_path = storage.get("data_path", "./data")

    for handler in handlers:
        sink = str(handler.get("sink", "")).replace("${DATA_PATH:./data}", data_path)
        Path(sink).parent.mkdir(parents=True, exist_ok=True)
        _logger.add(
            sink,
            level=handler.get("level", "INFO"),
            rotation=handler.get("rotation", "50 MB"),
            retention=handler.get("retention", "30 days"),
            compression=handler.get("compression", "gz"),
            format=handler.get("format", fmt),
        )

    _logger.info("Logging configured — level: {}", level)
