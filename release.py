"""Draft a time entry and release it to Sheets + Slack after confirm."""

from __future__ import annotations

import os
from datetime import date

from config import (
    SHEET_NAME,
    SHEETS_CONNECTED_ACCOUNT_ID,
    SLACK_CONNECTED_ACCOUNT_ID,
    SPREADSHEET_ID,
    USER_ID,
    composio,
    execute,
)
from infer import observe
from resolve import resolve_client
from task_classifier import classify_task

APPEND_TOOL = "GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND"
READ_TOOL = "GOOGLESHEETS_VALUES_GET"


def draft_from_fields(
    filename_hint: str,
    duration_minutes: int,
    raw_evidence: str,
    source: str = "FIXTURE",
    drive_file=None,
    gmail_subject=None,
    gum_confidence=None,
) -> dict:
    matter = resolve_client(filename_hint, raw_evidence)
    task = classify_task(raw_evidence)
    matter_name = matter.get("matter_name") or "unassigned matter"
    narrative = task["narrative_template"].format(matter_name=matter_name)
    hours = round(float(duration_minutes) / 60.0, 1)
    ready = (matter.get("confidence") or 0) >= 0.7 and duration_minutes >= 5
    hold_reasons = []
    if (matter.get("confidence") or 0) < 0.7:
        hold_reasons.append(matter.get("reason") or "low matter confidence")
    if duration_minutes < 5:
        hold_reasons.append(f"duration {duration_minutes}m is under 5 minutes")
    return {
        "filename_hint": filename_hint,
        "duration_minutes": duration_minutes,
        "raw_evidence": raw_evidence,
        "source": source,
        "drive_file": drive_file,
        "gmail_subject": gmail_subject,
        "gum_confidence": gum_confidence,
        "client": matter.get("client"),
        "matter_number": matter.get("matter_number"),
        "matter_name": matter.get("matter_name"),
        "confidence": matter.get("confidence"),
        "reason": matter.get("reason"),
        "task_type": task["task_type"],
        "narrative": narrative,
        "hours": hours,
        "date": date.today().isoformat(),
        "ready_to_confirm": ready,
        "hold_reasons": hold_reasons,
    }


def draft_list() -> list:
    """Only live observations. Empty if nothing was seen."""
    from infer import observe_list

    return [draft_entry(item) for item in observe_list()]


def draft_entry(observation: dict | None = None) -> dict:
    obs = observation or observe()
    entry = draft_from_fields(
        filename_hint=obs.get("filename_hint") or "",
        duration_minutes=int(obs.get("duration_minutes") or 0),
        raw_evidence=obs.get("raw_evidence") or "",
        source=obs.get("source") or "UNKNOWN",
        drive_file=obs.get("drive_file"),
        gmail_subject=obs.get("gmail_subject"),
        gum_confidence=obs.get("gum_confidence"),
    )
    if obs.get("minutes_ago") is not None:
        entry["minutes_ago"] = obs["minutes_ago"]
    if obs.get("summary"):
        entry["summary"] = obs["summary"]
    return entry


def _append_sheet(entry: dict) -> dict:
    return execute(
        APPEND_TOOL,
        {
            "spreadsheetId": SPREADSHEET_ID,
            "range": SHEET_NAME,
            "valueInputOption": "USER_ENTERED",
            "values": [[
                entry["client"] or "",
                entry["matter_number"] or "",
                entry["task_type"],
                entry["narrative"],
                entry["hours"],
                entry["date"],
            ]],
        },
        SHEETS_CONNECTED_ACCOUNT_ID,
    )


def _read_sheet() -> dict:
    return execute(
        READ_TOOL,
        {"spreadsheet_id": SPREADSHEET_ID, "range": SHEET_NAME},
        SHEETS_CONNECTED_ACCOUNT_ID,
    )


def _sheet_values(read_result: dict) -> list:
    data = read_result.get("data") if isinstance(read_result, dict) else {}
    return (data or {}).get("values") or []


def _slack_text(entry: dict) -> str:
    return (
        f"Released time entry: {entry['hours']}h · "
        f"{entry.get('matter_number') or 'no matter'} · "
        f"{entry['task_type']} — {entry['narrative']}"
    )


def _post_slack(entry: dict) -> dict:
    tools = composio.tools.get(user_id=USER_ID, toolkits=["SLACK"], limit=80)
    send_slugs = []
    for tool in tools:
        function = tool.get("function", tool) if isinstance(tool, dict) else tool
        name = function.get("name") if isinstance(function, dict) else getattr(function, "name", "")
        if name and any(k in name for k in ("SEND", "POST", "CHAT_POST")) and "MESSAGE" in name:
            send_slugs.append(name)
    preferred = [
        "SLACK_SEND_MESSAGE",
        "SLACK_CHAT_POST_MESSAGE",
        "SLACK_SENDS_A_MESSAGE_TO_A_SLACK_CHANNEL",
    ]
    ordered = [s for s in preferred if s in send_slugs] + [
        s for s in send_slugs if s not in preferred
    ]
    text = _slack_text(entry)
    last_error = "no Slack send tool found"
    for slug in ordered:
        for args in (
            {"text": text, "channel": os_channel()},
            {"text": text},
            {"message": text},
        ):
            try:
                return {"successful": True, "slug": slug, "result": execute(slug, args, SLACK_CONNECTED_ACCOUNT_ID)}
            except Exception as exc:
                last_error = f"{slug}: {exc}"
    return {"successful": False, "error": last_error}


def os_channel() -> str:
    return os.getenv("SLACK_CHANNEL") or "#general"


def release_entry(entry: dict) -> dict:
    append = _append_sheet(entry)
    readback = _read_sheet()
    values = _sheet_values(readback)
    verified = any(
        len(row) >= 4 and str(row[3]) == entry["narrative"]
        for row in values
    )
    slack = _post_slack(entry)
    return {
        "append": append,
        "readback": readback,
        "verified": verified,
        "slack": slack,
        "entry": entry,
    }
