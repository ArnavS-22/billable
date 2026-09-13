"""Live screen dumps for the tray. Written as soon as GUM sees a frame."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

LIVE_PATH = Path.home() / ".cache/gum" / "lawyer_obs.jsonl"


def append_observation(content: str, observer: str = "Screen") -> None:
    LIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "observer": observer,
        "content": (content or "")[:8000],
    }
    with LIVE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    _trim()


def _trim(keep: int = 200) -> None:
    if not LIVE_PATH.exists():
        return
    lines = LIVE_PATH.read_text(encoding="utf-8").splitlines()
    if len(lines) <= keep:
        return
    LIVE_PATH.write_text("\n".join(lines[-keep:]) + "\n", encoding="utf-8")


def load_recent(hours: int = 12, limit: int = 80) -> list[dict]:
    if not LIVE_PATH.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = []
    for line in LIVE_PATH.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        raw_ts = rec.get("ts") or ""
        try:
            ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts >= cutoff and rec.get("content"):
            rec["ts"] = ts
            rows.append(rec)
    return rows[-limit:]
