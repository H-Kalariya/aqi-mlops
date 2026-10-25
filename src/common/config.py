# Owner: Shared (M1 as repo/release manager) — Config loader
"""Load and validate config.yaml and params.yaml from the project root."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def _find_project_root() -> Path:
    """Walk up from this file to find the directory containing config.yaml."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "config.yaml").exists():
            return current
        current = current.parent
    raise FileNotFoundError("Cannot locate config.yaml in any parent directory")


PROJECT_ROOT: Path = _find_project_root()


def _resolve_env_vars(value: str) -> str:
    """Resolve ${ENV_VAR:-default} patterns in string values."""
    if not isinstance(value, str) or "${" not in value:
        return value

    import re

    pattern = r"\$\{(\w+)(?::-(.*?))?\}"

    def _replace(match: re.Match) -> str:
        env_var = match.group(1)
        default = match.group(2) if match.group(2) is not None else ""
        return os.environ.get(env_var, default)

    return re.sub(pattern, _replace, value)


def _resolve_recursive(obj: Any) -> Any:
    """Recursively resolve env vars in a nested dict/list."""
    if isinstance(obj, dict):
        return {k: _resolve_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_recursive(item) for item in obj]
    if isinstance(obj, str):
        return _resolve_env_vars(obj)
    return obj


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load config.yaml with env-var resolution.

    Args:
        path: Optional explicit path. Defaults to PROJECT_ROOT / config.yaml.

    Returns:
        Fully resolved configuration dictionary.
    """
    config_path = path or (PROJECT_ROOT / "config.yaml")
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    return _resolve_recursive(raw)


def load_params(path: Path | None = None) -> dict[str, Any]:
    """Load params.yaml.

    Args:
        path: Optional explicit path. Defaults to PROJECT_ROOT / params.yaml.

    Returns:
        Parameters dictionary.
    """
    params_path = path or (PROJECT_ROOT / "params.yaml")
    with open(params_path) as f:
        return yaml.safe_load(f)


# Convenience singletons — import once, use everywhere
_config: dict[str, Any] | None = None
_params: dict[str, Any] | None = None


def get_config() -> dict[str, Any]:
    """Return cached config, loading on first call."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_params() -> dict[str, Any]:
    """Return cached params, loading on first call."""
    global _params
    if _params is None:
        _params = load_params()
    return _params
