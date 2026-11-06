"""WebSocket API used by VirtuHome Pro's frontend module and the extensions it brings."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .automations import BLUEPRINT_ID, EXT_ID, BlueprintError
from .const import DOMAIN
from .extensions import ExtensionManager
from .licensing import LicenceError
from .repair_issues import async_update_issues


def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_extensions, ws_licence_get, ws_licence_activate, ws_licence_refresh, ws_licence_remove, ws_licence_trial,
        ws_catalog, ws_automations_list, ws_automations_preview, ws_automations_add, ws_automations_remove,
    ):
        websocket_api.async_register_command(hass, command)


def _manager(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> ExtensionManager | None:
    manager: ExtensionManager | None = hass.data.get(DOMAIN)
    if manager is None:
        connection.send_error(msg["id"], "not_loaded", "VirtuHome Pro is not set up")
    return manager


@websocket_api.websocket_command({vol.Required("type"): "virtuhome_pro/extensions"})
@callback
def ws_extensions(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """The extensions to load now, for every signed-in user (wall tablets too): id, name, version, url."""
    if (m := _manager(hass, connection, msg)) is None:
        return
    connection.send_result(msg["id"], m.extensions())


# ---------------------------------------------------------------------------- licence and extensions


async def _run(connection: websocket_api.ActiveConnection, msg: dict, coro) -> None:
    try:
        connection.send_result(msg["id"], await coro)
    except LicenceError as err:
        connection.send_error(msg["id"], "licence", str(err))
    except Exception as err:  # noqa: BLE001 - network trouble ends up in the UI as a message
        connection.send_error(msg["id"], "unreachable", f"The licence server could not be reached: {err}")


@websocket_api.websocket_command({vol.Required("type"): "virtuhome_pro/licence/get"})
@websocket_api.require_admin
@callback
def ws_licence_get(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    if (m := _manager(hass, connection, msg)) is None:
        return
    connection.send_result(msg["id"], m.summary())


@websocket_api.websocket_command(
    {vol.Required("type"): "virtuhome_pro/licence/activate", vol.Required("key"): vol.All(str, vol.Length(min=8, max=120))}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_licence_activate(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    if (m := _manager(hass, connection, msg)) is None:
        return
    await _run(connection, msg, m.async_activate(msg["key"]))


@websocket_api.websocket_command({vol.Required("type"): "virtuhome_pro/licence/refresh"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_licence_refresh(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    if (m := _manager(hass, connection, msg)) is None:
        return
    await _run(connection, msg, m.async_refresh())
    await async_update_issues(hass, m)


@websocket_api.websocket_command({vol.Required("type"): "virtuhome_pro/licence/remove"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_licence_remove(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    if (m := _manager(hass, connection, msg)) is None:
        return
    await _run(connection, msg, m.async_remove())


@websocket_api.websocket_command(
    {vol.Required("type"): "virtuhome_pro/licence/trial", vol.Required("ext"): vol.All(str, vol.Match(r"^[a-z0-9_]{1,40}$"))}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_licence_trial(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Starts a free trial of one extension in this home."""
    if (m := _manager(hass, connection, msg)) is None:
        return
    await _run(connection, msg, m.async_trial(msg["ext"]))


@websocket_api.websocket_command({vol.Required("type"): "virtuhome_pro/catalog"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_catalog(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """What extensions exist; only lists buy links once the shop is open on the server."""
    if (m := _manager(hass, connection, msg)) is None:
        return
    await _run(connection, msg, m.async_catalog())


# ---------------------------------------------------------------------------- automations from extensions' blueprints


async def _automations(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict, run) -> None:
    if (m := _manager(hass, connection, msg)) is None:
        return
    try:
        connection.send_result(msg["id"], await run(m.automations))
    except BlueprintError as err:
        connection.send_error(msg["id"], "blueprint", str(err))


EXTENSION = vol.All(str, vol.Match(EXT_ID))
ADD = {
    vol.Required("ext_id"): EXTENSION,
    vol.Required("blueprint"): vol.All(str, vol.Match(BLUEPRINT_ID)),
    # checked against the blueprint's inputs and their selectors (automations.check_inputs)
    vol.Optional("inputs", default={}): vol.Schema({vol.All(str, vol.Length(max=64)): object}),
    vol.Optional("alias", default=""): vol.All(str, vol.Length(max=100)),
    vol.Optional("description", default=""): vol.All(str, vol.Length(max=500)),
}


def _add_args(msg: dict[str, Any]) -> tuple:
    return msg["ext_id"], msg["blueprint"], msg["inputs"], msg["alias"], msg["description"]


@websocket_api.websocket_command({vol.Required("type"): "virtuhome_pro/automations/list", vol.Optional("ext_id"): EXTENSION})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_automations_list(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """The automations extensions added (one extension's with ext_id), as automations.yaml has them now."""
    await _automations(hass, connection, msg, lambda a: a.async_list(msg.get("ext_id")))


@websocket_api.websocket_command({vol.Required("type"): "virtuhome_pro/automations/preview", **ADD})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_automations_preview(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """What add would create (name, inputs, notify services, the automation as YAML), for the user to agree to."""
    await _automations(hass, connection, msg, lambda a: a.async_preview(*_add_args(msg)))


@websocket_api.websocket_command({vol.Required("type"): "virtuhome_pro/automations/add", **ADD})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_automations_add(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Adds an automation from a blueprint in an installed extension's signed bundle, once the user agreed."""
    await _automations(hass, connection, msg, lambda a: a.async_add(*_add_args(msg)))


@websocket_api.websocket_command({
    vol.Required("type"): "virtuhome_pro/automations/remove",
    vol.Required("ext_id"): EXTENSION,
    vol.Required("automation_id"): vol.All(str, vol.Length(max=100)),
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_automations_remove(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Removes one of the extension's automations (and its blueprint once no automation uses it)."""

    async def run(a):
        if not (removed := await a.async_remove(msg["ext_id"], {msg["automation_id"]})):
            raise BlueprintError("No such automation of this extension")
        return {"removed": removed}

    await _automations(hass, connection, msg, run)
