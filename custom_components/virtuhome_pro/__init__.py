"""VirtuHome Pro: extensions for VirtuHome, unlocked by a licence key.

VirtuHome itself has no licence code and loads no code from outside its repository. This integration
takes the licence key, downloads and checks the signed extension bundles (extensions.py), serves
them, and registers them with VirtuHome from its frontend module, which Home Assistant loads on
every page. VirtuHome hands each extension its API.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from awesomeversion import AwesomeVersion

from homeassistant.components.frontend import add_extra_js_url, remove_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from . import websocket
from .const import CONF_LICENCE_SERVER, CORE_DOMAIN, CORE_MIN_VERSION, DOMAIN, EXT_URL_BASE, MODULE_FILE, URL_BASE
from .extensions import ExtensionManager
from .repair_issues import async_update_issues

_LOGGER = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent / "frontend"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Static files and WebSocket commands: once per Home Assistant run (they can't be unregistered)."""
    ext_dir = Path(hass.config.path(".virtuhome", "extensions"))
    await hass.async_add_executor_job(lambda: ext_dir.mkdir(parents=True, exist_ok=True))
    await hass.http.async_register_static_paths([
        StaticPathConfig(URL_BASE, str(FRONTEND_DIR), cache_headers=False),
        # extension files carry their version in the name, so caching them is safe
        StaticPathConfig(EXT_URL_BASE, str(ext_dir), cache_headers=True),
    ])
    websocket.async_register(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # VirtuHome up to 0.17 handled the licence itself, from the same store: never both at once
    core = await async_get_integration(hass, CORE_DOMAIN)
    if AwesomeVersion(str(core.version)) < AwesomeVersion(CORE_MIN_VERSION):
        ir.async_create_issue(
            hass, DOMAIN, "virtuhome_too_old", is_fixable=False, is_persistent=False,
            severity=ir.IssueSeverity.ERROR, translation_key="virtuhome_too_old",
            translation_placeholders={"version": str(core.version), "needed": CORE_MIN_VERSION},
        )
        raise ConfigEntryError(f"VirtuHome Pro needs VirtuHome {CORE_MIN_VERSION} or later; this is {core.version}")
    ir.async_delete_issue(hass, DOMAIN, "virtuhome_too_old")

    manager = ExtensionManager(hass, entry.options.get(CONF_LICENCE_SERVER))
    await manager.async_load()
    hass.data[DOMAIN] = manager
    entry.async_on_unload(manager.async_unload)
    entry.async_on_unload(entry.add_update_listener(_options_updated))

    # the frontend module registers the extensions with VirtuHome, on every page
    version = str((await async_get_integration(hass, DOMAIN)).version)
    module_url = f"{URL_BASE}/{MODULE_FILE}?v={version}"
    add_extra_js_url(hass, module_url)
    entry.async_on_unload(lambda: remove_extra_js_url(hass, module_url))

    async def _update_issues(_now: Any = None) -> None:
        try:
            await async_update_issues(hass, manager)
        except Exception:  # noqa: BLE001 - Repairs are a convenience; extensions work without them
            _LOGGER.exception("Could not update VirtuHome Pro's repair issues")

    # a licence that stops renewing shows up in Repairs within a day
    entry.async_on_unload(async_track_time_interval(hass, _update_issues, timedelta(hours=24)))
    await _update_issues()
    return True


async def _options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.pop(DOMAIN, None)
    return True
