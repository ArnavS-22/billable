"""Read GUM's local DB and fuse Drive / Gmail corroboration."""

from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timedelta, timezone

from config import DRIVE_CONNECTED_ACCOUNT_ID, DRIVE_FIND_TOOL, GMAIL_CONNECTED_ACCOUNT_ID, execute
from matters import MATTERS
from resolve import resolve_client
from task_classifier import classify_task

_FILENAME_RE = re.compile(
    r"[\w.-]+\.(?:docx?|pdf|xlsx?|pptx?|txt|gdoc)|[A-Za-z0-9]+_[A-Za-z0-9_]+",
    re.I,
)
_LEGAL_RE = re.compile(
    r"\b(nda|redline|westlaw|lexis|pacer|ecf|term sheet|indemnif|escrow|bylaws)\b",
    re.I,
)
_NOT_LEGAL_RE = re.compile(
    r"chatgpt|openai|claude\.ai|cursor ide|uvicorn|fastapi|"
    r"position paper|chi position|gum lawyer|screenshot \d",
    re.I,
)


def _prop_text(prop) -> str:
    if isinstance(prop, tuple):
        prop = prop[0]
    parts = [getattr(prop, "text", None) or ""]
    reasoning = getattr(prop, "reasoning", None)
    if reasoning:
        parts.append(str(reasoning))
    return "\n".join(p for p in parts if p)


def _matter_hit(text: str) -> str | None:
    lowered = (text or "").lower()
    for key, info in MATTERS.items():
        number = str(info.get("matter_number") or "").lower()
        if key.lower() in lowered or (number and number in lowered):
            return key
    return None


def _is_billable_screen(text: str) -> bool:
    if not text:
        return False
    if _matter_hit(text) or _LEGAL_RE.search(text):
        if _NOT_LEGAL_RE.search(text) and not _matter_hit(text) and not re.search(r"\bnda\b", text, re.I):
            return False
        return True
    return False


def _legal_excerpt(text: str) -> str:
    pieces = re.split(r"[\n.]+", text or "")
    keep = [
        p.strip()
        for p in pieces
        if (_matter_hit(p) or _LEGAL_RE.search(p)) and not _NOT_LEGAL_RE.search(p)
    ]
    if keep:
        return ". ".join(keep)[:400]
    hit = _matter_hit(text or "")
    if hit:
        return f"Screen activity on {hit} matter."
    return "Screen activity on a matter file."


def _extract_filename(text: str) -> str | None:
    if not text:
        return None
    hit = _matter_hit(text)
    if hit:
        match = _FILENAME_RE.search(text)
        return match.group(0) if match else hit
    if not _is_billable_screen(text):
        return None
    match = _FILENAME_RE.search(text)
    return match.group(0) if match else None


def _created_at(obj):
    created = getattr(obj, "created_at", None)
    if created is None:
        return None
    if isinstance(created, str):
        try:
            created = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError:
            return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return created


def _is_fresh(obj, hours: int = 12) -> bool:
    created = _created_at(obj)
    if created is None:
        return False
    return created >= datetime.now(timezone.utc) - timedelta(hours=hours)


def _duration_from_obs(observations) -> int | None:
    times = []
    for obs in observations or []:
        created = getattr(obs, "created_at", None)
        if created is None:
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        times.append(created)
    if len(times) < 2:
        return None
    span = (max(times) - min(times)).total_seconds() / 60.0
    if span < 1:
        return None
    return max(6, int(round(span)))


async def _query_gum() -> dict | None:
    try:
        from gum import gum
    except ImportError:
        return None

    user_name = os.getenv("USER_NAME") or os.getenv("GUM_USER_NAME") or "Lawyer"
    model = os.getenv("MODEL_NAME") or "gpt-4o-mini"
    try:
        instance = gum(user_name, model)
        await instance.connect_db()
        recent = await instance.recent(limit=15)
        hits = []
        try:
            hits = await instance.query(
                "draft review NDA email research matter redline markup",
                limit=10,
            )
        except Exception:
            hits = []
        observations = []
        if hasattr(instance, "recent_observations"):
            try:
                observations = await instance.recent_observations(limit=20)
            except Exception:
                observations = []
    except Exception:
        return None

    recent = [p for p in (recent or []) if _is_fresh(p)]
    hits = [h for h in (hits or []) if _is_fresh(h[0] if isinstance(h, tuple) else h)]
    observations = [o for o in (observations or []) if _is_fresh(o)]

    blobs = [_prop_text(p) for p in recent]
    blobs.extend(_prop_text(h) for h in hits)
    for obs in observations:
        content = getattr(obs, "content", None)
        if content:
            blobs.append(str(content))
    raw = "\n".join(b for b in blobs if b).strip()
    if len(raw) < 20:
        return None

    confidences = []
    for item in list(recent or []) + [h[0] if isinstance(h, tuple) else h for h in (hits or [])]:
        conf = getattr(item, "confidence", None)
        if conf is not None:
            try:
                confidences.append(float(conf))
            except (TypeError, ValueError):
                pass

    filename = _extract_filename(raw)
    duration = _duration_from_obs(observations)
    if duration is None:
        duration = 12 if filename else 8

    return {
        "filename_hint": filename or "unknown",
        "duration_minutes": duration,
        "raw_evidence": raw[:4000],
        "source": "LIVE GUM DATA",
        "gum_confidence": max(confidences) / 10.0 if confidences else None,
        "drive_file": None,
        "gmail_subject": None,
    }


def _drive_match(filename_hint: str) -> dict | None:
    if not filename_hint or filename_hint == "unknown":
        return None
    try:
        result = execute(
            DRIVE_FIND_TOOL,
            {
                "q": f"name contains '{filename_hint.split('.')[0][:40]}' and trashed = false",
                "pageSize": 5,
                "fields": "files(id,name)",
            },
            DRIVE_CONNECTED_ACCOUNT_ID,
        )
    except Exception:
        return None
    data = result.get("data") if isinstance(result, dict) else {}
    files = (data or {}).get("files") or []
    if not files:
        return None
    first = files[0]
    return {"id": first.get("id"), "name": first.get("name")}


def _gmail_subject(evidence: str) -> str | None:
    if not any(k in evidence.lower() for k in ("email", "gmail", "correspond", "reply")):
        return None
    for slug, args in (
        ("GMAIL_FETCH_EMAILS", {"max_results": 3}),
        ("GMAIL_LIST_MESSAGES", {"max_results": 3}),
        ("GMAIL_GET_PROFILE", {}),
    ):
        try:
            result = execute(slug, args, GMAIL_CONNECTED_ACCOUNT_ID)
        except Exception:
            continue
        data = result.get("data") if isinstance(result, dict) else {}
        messages = (
            (data or {}).get("messages")
            or (data or {}).get("emails")
            or []
        )
        if messages:
            first = messages[0]
            return first.get("subject") or first.get("snippet") or str(first)[:120]
        if slug == "GMAIL_GET_PROFILE" and data:
            return None
    return None


def _cluster_key(text: str) -> str | None:
    if not _is_billable_screen(text):
        return None
    hit = _matter_hit(text)
    if hit:
        return hit
    filename = _extract_filename(text or "")
    if filename:
        return filename.lower()
    return None


def _clusters_from_rows(rows: list[dict]) -> list[dict]:
    buckets: dict[str, list[dict]] = {}
    for row in rows:
        content = str(row.get("content") or "")
        if len(content.strip()) < 20:
            continue
        key = _cluster_key(content)
        if not key:
            continue
        buckets.setdefault(key, []).append(row)

    clusters = []
    for key, group in buckets.items():
        texts = [str(item.get("content") or "") for item in group]
        raw = _legal_excerpt("\n".join(texts))
        times = [item["ts"] for item in group if item.get("ts")]
        if len(times) >= 2:
            span = int(round((max(times) - min(times)).total_seconds() / 60.0))
            duration = max(6, span) if span >= 1 else max(6, len(group) * 2)
        else:
            duration = max(6, len(group) * 2)
        filename = _extract_filename(" ".join(texts))
        if key in MATTERS:
            filename = filename or key
        clusters.append(
            {
                "filename_hint": filename or key,
                "duration_minutes": duration,
                "raw_evidence": raw,
                "source": "LIVE GUM DATA",
                "gum_confidence": None,
                "drive_file": None,
                "gmail_subject": None,
            }
        )
    clusters.sort(key=lambda item: item["filename_hint"])
    return clusters


def _obs_from_row(row: dict) -> dict:
    content = str(row.get("content") or "")
    excerpt = _legal_excerpt(content)
    key = _cluster_key(content)
    filename = _extract_filename(content)
    if key in MATTERS:
        filename = filename or key
    ts = row.get("ts")
    ago = 0
    if ts is not None:
        now = datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ago = max(0, int((now - ts).total_seconds() / 60))
    return {
        "filename_hint": filename or key or "unknown",
        "duration_minutes": 5 if ago >= 5 else max(3, ago or 3),
        "raw_evidence": excerpt,
        "source": "LIVE GUM DATA",
        "gum_confidence": None,
        "drive_file": None,
        "gmail_subject": None,
        "minutes_ago": ago,
        "summary": excerpt[:90],
    }


def observe_list() -> list[dict]:
    """One tray row per fresh billable screen dump. No batch queue."""
    try:
        from gum_lawyer.live import load_recent

        rows = load_recent()
    except Exception:
        rows = []
    instant = []
    for row in rows:
        content = str(row.get("content") or "")
        if not _cluster_key(content):
            continue
        instant.append(_obs_from_row(row))
        if len(instant) >= 8:
            instant = instant[-8:]
    if instant:
        return instant

    live = None
    try:
        live = asyncio.run(_query_gum())
    except Exception:
        live = None
    if live and (
        _is_billable_screen(live.get("raw_evidence") or "")
        or _is_billable_screen(live.get("filename_hint") or "")
    ):
        live["raw_evidence"] = _legal_excerpt(live.get("raw_evidence") or "")
        return [live]
    return []


def _enrich(observation: dict) -> dict:
    observation = dict(observation)
    hint = observation.get("filename_hint") or ""
    evidence = observation.get("raw_evidence") or ""
    observation["drive_file"] = observation.get("drive_file") or _drive_match(hint)
    observation["gmail_subject"] = observation.get("gmail_subject") or _gmail_subject(evidence)
    extra = " ".join(
        filter(
            None,
            [
                evidence,
                (observation.get("drive_file") or {}).get("name"),
                observation.get("gmail_subject"),
            ],
        )
    )
    observation["matter"] = resolve_client(hint, extra)
    observation["task"] = classify_task(evidence)
    return observation


def observe() -> dict:
    """Return a live observation, or an empty hold if nothing was seen."""
    lives = observe_list()
    if lives:
        return _enrich(dict(lives[0]))
    return _enrich(
        {
            "filename_hint": "",
            "duration_minutes": 0,
            "raw_evidence": "",
            "source": "NO DATA",
            "gum_confidence": None,
            "drive_file": None,
            "gmail_subject": None,
        }
    )
