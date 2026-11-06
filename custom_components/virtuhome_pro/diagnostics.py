"""Settings → Devices & services → VirtuHome Pro → ⋮ → Download diagnostics (report.py says what's in it)."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data
from homeassistant.loader import IntegrationNotFound, async_get_integration

from .const import CORE_DOMAIN, DOMAIN
from .report import TO_REDACT, build_report


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    manager = hass.data.get(DOMAIN)
    try:
        core_version: str | None = str((await async_get_integration(hass, CORE_DOMAIN)).version)
    except IntegrationNotFound:
        core_version = None
    report = build_report(
        version=str((await async_get_integration(hass, DOMAIN)).version),
        core_version=core_version,
        ha_version=HA_VERSION,
        options=dict(entry.options),
        summary=manager.summary() if manager else None,
        loaded=manager.extensions() if manager else [],
    )
    return async_redact_data(report, TO_REDACT)
