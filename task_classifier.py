"""Keyword task classifier. Drafting keywords are checked first."""

DRAFTING = ("redline", "markup", "revise", "draft")
REVIEW = ("review", "read", "analyz")
CORRESPONDENCE = ("email", "correspond", "reply")
RESEARCH = ("research", "search", "case law", "westlaw", "lexis")
LEGAL_CONTEXT = (
    "nda",
    "agreement",
    "contract",
    "clause",
    "matter",
    "redline",
    "markup",
    "westlaw",
    "lexis",
    "term sheet",
)


def _legalish(text: str) -> bool:
    return any(k in text for k in LEGAL_CONTEXT)


def classify_task(evidence_text: str) -> dict:
    text = (evidence_text or "").lower()
    if any(k in text for k in DRAFTING) and _legalish(text):
        return {
            "task_type": "Document Drafting/Revision",
            "narrative_template": "Reviewed and revised {matter_name}; prepared markup and comments",
        }
    if any(k in text for k in REVIEW):
        return {
            "task_type": "Document Review",
            "narrative_template": "Reviewed and analyzed {matter_name}",
        }
    if any(k in text for k in CORRESPONDENCE):
        return {
            "task_type": "Correspondence",
            "narrative_template": "Correspondence with client re: {matter_name}",
        }
    if any(k in text for k in RESEARCH):
        return {
            "task_type": "Legal Research",
            "narrative_template": "Conducted legal research regarding {matter_name}",
        }
    return {
        "task_type": "General Matter Work",
        "narrative_template": "Attended to matters regarding {matter_name}",
    }
