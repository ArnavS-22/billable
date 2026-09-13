"""Drive listing plus matter resolution against MATTERS."""

from matters import MATTERS
from config import (
    DRIVE_CONNECTED_ACCOUNT_ID,
    DRIVE_FIND_TOOL,
    USER_ID,
    composio,
    execute,
)


def _tool_name(tool):
    function = tool.get("function", tool) if isinstance(tool, dict) else tool
    if isinstance(function, dict):
        return function.get("name")
    return getattr(function, "name", None)


def print_candidate_drive_tools():
    tools = composio.tools.get(
        user_id=USER_ID,
        toolkits=["GOOGLEDRIVE"],
        limit=100,
    )
    print("=== Google Drive list/search candidates ===")
    keywords = ("LIST", "SEARCH", "FIND")
    for tool in tools:
        name = _tool_name(tool) or ""
        if any(k in name.upper() for k in keywords) and "FILE" in name.upper():
            print(name)
    return tools


def list_recent_drive_files():
    print_candidate_drive_tools()
    print()

    result = execute(
        DRIVE_FIND_TOOL,
        {
            "q": "trashed = false",
            "orderBy": "modifiedTime desc",
            "pageSize": 20,
            "fields": "files(id,name,modifiedTime,mimeType)",
        },
        DRIVE_CONNECTED_ACCOUNT_ID,
    )

    data = result.get("data") if isinstance(result, dict) else result
    files = []
    if isinstance(data, dict):
        files = data.get("files") or data.get("items") or []
        if not files and isinstance(data.get("response_data"), dict):
            files = data["response_data"].get("files") or []

    print("=== Recent Drive files ===")
    if not files:
        print("No files returned. Raw result:")
        print(result)
        return []

    for file in files:
        name = file.get("name") if isinstance(file, dict) else getattr(file, "name", None)
        file_id = file.get("id") if isinstance(file, dict) else getattr(file, "id", None)
        print(f"{name}  {file_id}")
    return files


def resolve_client(filename: str, extra: str = "") -> dict:
    """Resolve a matter from filename / evidence text against MATTERS."""
    haystack = f"{filename or ''} {extra or ''}".lower()
    matches = [(key, info) for key, info in MATTERS.items() if key in haystack]

    if len(matches) == 1:
        matched_key, info = matches[0]
        return {
            "client": info["client"],
            "matter_number": info["matter_number"],
            "matter_name": info["matter_name"],
            "confidence": 0.9,
            "reason": f"filename contains '{matched_key}'",
        }
    if len(matches) == 0:
        return {
            "client": None,
            "matter_number": None,
            "matter_name": None,
            "confidence": 0.0,
            "reason": "no known client name found in filename",
        }
    return {
        "client": None,
        "matter_number": None,
        "matter_name": None,
        "confidence": 0.3,
        "reason": "multiple possible clients matched, ambiguous",
    }


resolve_matter = resolve_client


if __name__ == "__main__":
    files = list_recent_drive_files()
    print()
    print("=== Matter resolution ===")
    for file in files:
        name = file.get("name") if isinstance(file, dict) else getattr(file, "name", None)
        print(f"{name}  {resolve_client(name or '')}")
