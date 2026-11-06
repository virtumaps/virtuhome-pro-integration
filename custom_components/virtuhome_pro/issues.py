"""What VirtuHome Pro tells Home Assistant's Repairs (no Home Assistant imports: testable alone)."""

from __future__ import annotations

from typing import Any

# the issues repair_issues.py keeps up to date; their texts are under "issues" in strings.json
# (virtuhome_too_old is raised by __init__.py while setting up)
ISSUE_IDS = ("licence_not_renewed",)
# a licence key that hasn't been renewed for this long is worth a repair
LICENCE_DAYS = 30


def found_issues(licence: dict[str, Any] | None, now: float) -> dict[str, dict[str, str]]:
    """Issue id -> translation placeholders, for the issues that apply now."""
    out: dict[str, dict[str, str]] = {}
    if licence and licence.get("key_hint") and licence.get("status") not in (None, "none"):
        checked = licence.get("checked")
        if isinstance(checked, (int, float)) and now - checked > LICENCE_DAYS * 86400:
            out["licence_not_renewed"] = {"days": str(int((now - checked) // 86400)), "error": str(licence.get("error") or "")}
    return out
