"""CLI: draft a time entry from GUM (or fallback); --confirm releases it."""

from __future__ import annotations

import argparse
import json

from release import draft_entry, release_entry


def print_draft(entry: dict) -> None:
    print(f"SOURCE: {entry['source']}")
    print(f"filename_hint: {entry['filename_hint']}")
    print(f"duration_minutes: {entry['duration_minutes']}")
    print(f"client: {entry['client']}")
    print(f"matter_number: {entry['matter_number']}")
    print(f"matter_name: {entry['matter_name']}")
    print(f"confidence: {entry['confidence']}  ({entry['reason']})")
    print(f"task_type: {entry['task_type']}")
    print(f"hours: {entry['hours']}")
    print(f"date: {entry['date']}")
    print(f"narrative: {entry['narrative']}")
    if entry.get("drive_file"):
        print(f"drive_file: {entry['drive_file']}")
    if entry.get("gmail_subject"):
        print(f"gmail_subject: {entry['gmail_subject']}")
    print()
    print("raw_evidence:")
    print(entry["raw_evidence"])
    print()
    if entry["ready_to_confirm"]:
        print("GATE: ready to confirm (confidence >= 0.7 and duration >= 5)")
    else:
        print("GATE: NEEDS CONFIRMATION / HOLD")
        for reason in entry["hold_reasons"]:
            print(f"  - {reason}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Draft or release a lawyer time entry")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Write the draft to Google Sheets and Slack (review-then-release)",
    )
    args = parser.parse_args()

    entry = draft_entry()
    print_draft(entry)

    if not args.confirm:
        print()
        print("Nothing written. Re-run with --confirm to release, or open the review tray (python app.py).")
        return

    if not entry["ready_to_confirm"]:
        print()
        print("NEEDS CONFIRMATION — refusing to write from CLI. Use the tray to force-edit and confirm.")
        return

    result = release_entry(entry)
    print()
    if result["verified"]:
        print("AUTO-LOGGED AND VERIFIED" if entry["ready_to_confirm"] else "RELEASED AND VERIFIED")
    else:
        print("WROTE BUT READ-BACK DID NOT VERIFY")
    print(json.dumps({
        "verified": result["verified"],
        "slack_ok": result["slack"].get("successful"),
        "narrative": entry["narrative"],
        "hours": entry["hours"],
    }, indent=2))


if __name__ == "__main__":
    main()
