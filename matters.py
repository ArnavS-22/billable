"""Matter directory loaded from env or matters.json. Nothing is baked in."""

from __future__ import annotations

import json
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def load_matters() -> dict:
    raw = os.getenv("MATTERS_JSON")
    if raw:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    path = Path(os.getenv("MATTERS_FILE") or _ROOT / "matters.json")
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    return {}


MATTERS = load_matters()
