"""Local review tray: draft from GUM, lawyer confirms, then Sheets + Slack."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from release import draft_entry, draft_list, release_entry

app = FastAPI(title="Billable review tray")
HOME = Path(__file__).parent / "templates" / "home.html"
TEMPLATE = Path(__file__).parent / "templates" / "tray.html"


class ReleaseBody(BaseModel):
    narrative: str | None = None
    hours: float | None = None
    date: str | None = None
    client: str | None = None
    matter_number: str | None = None
    task_type: str | None = None
    filename_hint: str | None = None
    duration_minutes: int | None = None
    raw_evidence: str | None = None
    source: str | None = None
    matter_name: str | None = None
    confidence: float | None = None
    reason: str | None = None
    ready_to_confirm: bool | None = None
    hold_reasons: list | None = None
    drive_file: dict | None = None
    gmail_subject: str | None = None
    gum_confidence: float | None = None


@app.get("/", response_class=HTMLResponse)
def home():
    return HOME.read_text(encoding="utf-8")


@app.get("/app", response_class=HTMLResponse)
def tray():
    return TEMPLATE.read_text(encoding="utf-8")


@app.get("/api/draft")
def api_draft():
    entries = draft_list()
    payload = {"entries": entries}
    if entries:
        payload.update(entries[0])
    return payload


@app.post("/api/release")
def api_release(body: ReleaseBody):
    entry = draft_entry()
    updates = body.model_dump(exclude_none=True)
    entry.update(updates)
    result = release_entry(entry)
    return {
        "verified": result["verified"],
        "slack_ok": result["slack"].get("successful"),
        "slack_error": result["slack"].get("error"),
        "entry": result["entry"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
