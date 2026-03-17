from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "model"


def _load_with_python_dotenv(path: Path) -> bool:
    try:
        from dotenv import dotenv_values  # type: ignore
    except Exception:
        return False

    if not path.exists():
        return True

    values = dotenv_values(str(path))
    for k, v in values.items():
        if not k or v is None:
            continue
        os.environ.setdefault(str(k), str(v))
    return True


def _parse_dotenv_minimal(dotenv_path: Path) -> dict[str, str]:
    """
    Fallback .env parser (used only if python-dotenv isn't available).
    """
    env: dict[str, str] = {}
    if not dotenv_path.exists():
        return env

    for raw in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in env:
            env[key] = value
    return env


def load_env(dotenv_path: Optional[Path] = None) -> None:
    """
    Load variables from .env into process environment (no override).
    Prefers python-dotenv; falls back to minimal parser.
    """
    path = dotenv_path or (PROJECT_ROOT / ".env")
    if _load_with_python_dotenv(path):
        return
    for k, v in _parse_dotenv_minimal(path).items():
        os.environ.setdefault(k, v)


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    load_env()
    return os.getenv(key, default)

