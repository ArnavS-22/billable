"""Shared Composio + GUM constants. IDs come from the environment."""

import os

from dotenv import load_dotenv
from composio import Composio

load_dotenv()


def _need(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"{name} is empty. Copy .env.example to .env and fill it in.")
    return value


api_key = _need("COMPOSIO_API_KEY")
composio = Composio(api_key=api_key)

USER_ID = _need("COMPOSIO_USER_ID")
SPREADSHEET_ID = _need("SPREADSHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME") or "Sheet1"

SHEETS_CONNECTED_ACCOUNT_ID = _need("SHEETS_CONNECTED_ACCOUNT_ID")
DRIVE_CONNECTED_ACCOUNT_ID = _need("DRIVE_CONNECTED_ACCOUNT_ID")
GMAIL_CONNECTED_ACCOUNT_ID = _need("GMAIL_CONNECTED_ACCOUNT_ID")
SLACK_CONNECTED_ACCOUNT_ID = _need("SLACK_CONNECTED_ACCOUNT_ID")

APPEND_TOOL = "GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND"
READ_TOOL = "GOOGLESHEETS_VALUES_GET"
DRIVE_FIND_TOOL = "GOOGLEDRIVE_FIND_FILE"


def execute(slug, arguments, connected_account_id):
    return composio.tools.execute(
        slug,
        arguments,
        user_id=USER_ID,
        connected_account_id=connected_account_id,
        dangerously_skip_version_check=True,
    )
