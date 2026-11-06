"""Keeps VirtuHome Pro's issues in Home Assistant's Repairs up to date (what they are: issues.py)."""

from __future__ import annotations

import time

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .extensions import ExtensionManager
from .issues import ISSUE_IDS, found_issues

GUIDE = "https://virtumaps.github.io/virtuhome/#extensions-and-virtuhome-pro"


async def async_update_issues(hass: HomeAssistant, manager: ExtensionManager | None) -> None:
    """Raises the issues that apply now and takes away those that went."""
    if manager is None:
        return
    found = found_issues(manager.summary(), time.time())
    for issue_id in ISSUE_IDS:
        if issue_id in found:
            ir.async_create_issue(
                hass, DOMAIN, issue_id, is_fixable=False, is_persistent=False,
                severity=ir.IssueSeverity.WARNING, translation_key=issue_id,
                translation_placeholders=found[issue_id], learn_more_url=GUIDE,
            )
        else:
            ir.async_delete_issue(hass, DOMAIN, issue_id)
