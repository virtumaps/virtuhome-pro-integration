"""Adds, lists and removes the automations extensions make from their blueprints (see automations.py).

Done through Home Assistant's own code, as its editors do it: the blueprint goes in through the
automation blueprints' DomainBlueprints (as Settings → Blueprints imports one), and the automation is
validated with the automation editor's validator, added to automations.yaml with Home Assistant's
YAML loader and dumper (as the editor's config view writes it), and reloaded on its own.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.config import AUTOMATION_CONFIG_PATH
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er
from homeassistant.util.file import write_utf8_file_atomic
from homeassistant.util.yaml import dump, load_yaml, parse_yaml

from .automations import (
    EXT_ID, FOLDER, ID_PREFIX, BlueprintError, blueprint_path, blueprints_in_use, check_inputs, describe, listed,
    new_automation, notify_targets, remove_from, signed_blueprint,
)
from .licensing import verify_bundle

if TYPE_CHECKING:
    from .extensions import ExtensionManager

_LOGGER = logging.getLogger(__name__)
AUTOMATION = "automation"
WHAT_IT_DOES = ("triggers", "trigger", "conditions", "condition", "actions", "action")


class AutomationStore:
    def __init__(self, hass: HomeAssistant, manager: ExtensionManager) -> None:
        self.hass = hass
        self.manager = manager
        self.file = Path(hass.config.path(AUTOMATION_CONFIG_PATH))
        self.folder = Path(hass.config.path("blueprints", AUTOMATION, FOLDER))
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ automations.yaml

    def _read(self) -> list[Any]:
        if not self.file.is_file():
            return []
        data = load_yaml(str(self.file)) or []
        if not isinstance(data, list):
            raise BlueprintError("automations.yaml isn't a list of automations")
        return data

    def _write(self, configs: list[Any]) -> None:
        write_utf8_file_atomic(str(self.file), dump(configs))

    def _exists(self, kind: str, value: str) -> bool:
        if kind == "entity":
            return self.hass.states.get(value) is not None or er.async_get(self.hass).async_get(value) is not None
        if kind == "device":
            return dr.async_get(self.hass).async_get(value) is not None
        return ar.async_get(self.hass).async_get_area(value) is not None

    # ------------------------------------------------------------------ what the frontend asks

    async def _prepare(self, ext_id: str, bp_id: str, given: dict[str, Any], alias: str, description: str) -> dict[str, Any]:
        """The blueprint from the extension's signed bundle, the checked inputs, and the automation."""
        from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA  # noqa: PLC0415
        from homeassistant.components.blueprint import Blueprint, BlueprintInputs  # noqa: PLC0415

        if AUTOMATION not in self.hass.config.components:
            raise BlueprintError("Home Assistant's automations aren't set up")
        ext = next((e for e in self.manager.installed() if e["id"] == ext_id), None)
        if ext is None:
            raise BlueprintError(f"{ext_id} isn't installed")
        bundle = await self.hass.async_add_executor_job((self.manager.folder / ext["file"]).read_bytes)
        text = signed_blueprint(ext, bundle, bp_id, verify_bundle)
        path = blueprint_path(ext_id, bp_id)
        try:
            blueprint = Blueprint(parse_yaml(text), path=path, expected_domain=AUTOMATION, schema=AUTOMATION_BLUEPRINT_SCHEMA)
        except HomeAssistantError as err:
            raise BlueprintError(f"{ext_id}'s blueprint {bp_id!r} isn't valid: {err}") from err
        info = describe(blueprint.metadata, blueprint.inputs)
        inputs = check_inputs(info["inputs"], given, self._exists)
        config = new_automation(f"{ID_PREFIX}{ext_id}-{secrets.token_hex(6)}", alias.strip() or info["name"], description.strip(), path, inputs)
        try:
            bp_inputs = BlueprintInputs(blueprint, config)
            bp_inputs.validate()
            resolved = bp_inputs.async_substitute()
        except Exception as err:  # noqa: BLE001 - Home Assistant's own reasons, shown as they are
            raise BlueprintError(str(err)) from err
        return {"blueprint": blueprint, "text": text, "info": info, "config": config, "resolved": resolved}

    async def async_preview(self, ext_id: str, bp_id: str, given: dict[str, Any], alias: str = "", description: str = "") -> dict[str, Any]:
        """What add() would create, for the agreement dialog. Nothing is written."""
        p = await self._prepare(ext_id, bp_id, given, alias, description)
        info, config, resolved = p["info"], p["config"], p["resolved"]
        return {
            "alias": config["alias"],
            "description": config.get("description", ""),
            "blueprint": {"id": bp_id, "path": config["use_blueprint"]["path"], "name": info["name"],
                          "description": info["description"], "yaml": p["text"]},
            "inputs": [{"key": k, "name": info["inputs"][k]["name"], "value": v} for k, v in config["use_blueprint"]["input"].items()],
            "notify": notify_targets(resolved),
            # the triggers, conditions and actions with the inputs filled in, as YAML
            "yaml": dump({k: resolved[k] for k in WHAT_IT_DOES if k in resolved}),
        }

    async def async_add(self, ext_id: str, bp_id: str, given: dict[str, Any], alias: str = "", description: str = "") -> dict[str, Any]:
        """Writes the blueprint and adds the automation (call only after the user agreed)."""
        from homeassistant.components.automation.config import async_validate_config_item  # noqa: PLC0415
        from homeassistant.components.automation.helpers import async_get_blueprints  # noqa: PLC0415

        p = await self._prepare(ext_id, bp_id, given, alias, description)
        config, blueprint = p["config"], p["blueprint"]
        path = config["use_blueprint"]["path"]
        run = self.hass.async_add_executor_job
        async with self._lock:
            # written when new or changed by an update (Home Assistant then reloads the automations using it)
            target = self.folder.parent / path
            current = await run(lambda: target.read_text(encoding="utf-8") if target.is_file() else None)
            if current != blueprint.yaml():
                await async_get_blueprints(self.hass).async_add_blueprint(blueprint, path, allow_override=True)
            try:
                await async_validate_config_item(self.hass, config["id"], config)
            except Exception as err:  # noqa: BLE001
                raise BlueprintError(f"Home Assistant refused the automation: {err}") from err
            existed = await run(self.file.is_file)
            configs = await run(self._read)
            await run(self._write, [*configs, config])
        await self.hass.services.async_call(AUTOMATION, "reload", {"id": config["id"]}, blocking=True)
        entity_id = er.async_get(self.hass).async_get_entity_id(AUTOMATION, AUTOMATION, config["id"])
        if entity_id is None:
            await self.async_remove(ext_id, {config["id"]})
            if not existed:
                await run(lambda: self.file.unlink(missing_ok=True))
            raise BlueprintError(
                "Home Assistant doesn't load automations.yaml, so automations made in its editor don't work here "
                "either (configuration.yaml needs automation: !include automations.yaml)"
            )
        return {"id": config["id"], "entity_id": entity_id}

    async def async_list(self, ext_id: str | None = None) -> list[dict[str, Any]]:
        registry = er.async_get(self.hass)
        out = listed(await self.hass.async_add_executor_job(self._read), ext_id)
        for item in out:
            entity_id = registry.async_get_entity_id(AUTOMATION, AUTOMATION, item["id"])
            state = self.hass.states.get(entity_id) if entity_id else None
            item.update(entity_id=entity_id, state=state.state if state else None)
        return out

    async def async_remove(self, ext_id: str, ids: set[str] | None = None) -> list[str]:
        """Removes the extension's automations (those in ids, or all) and the blueprints of it no automation uses."""
        run = self.hass.async_add_executor_job
        async with self._lock:
            configs = await run(self._read)
            kept, gone = remove_from(configs, ext_id, ids)
            if gone:
                await run(self._write, kept)
        # as the automation editor deletes one: its entity goes with its registry entry
        registry = er.async_get(self.hass)
        removed_entities = [e for a in gone if (e := registry.async_get_entity_id(AUTOMATION, AUTOMATION, a))]
        for entity_id in removed_entities:
            registry.async_remove(entity_id)
        await self._drop_blueprints(ext_id, blueprints_in_use(kept), removed_entities)
        return gone

    async def _drop_blueprints(self, ext_id: str, in_use: set[str], removed: list[str]) -> None:
        from homeassistant.components.automation import automations_with_blueprint  # noqa: PLC0415
        from homeassistant.components.automation.helpers import async_get_blueprints  # noqa: PLC0415
        from homeassistant.components.blueprint import BlueprintException  # noqa: PLC0415

        folder = self.folder / ext_id
        files = await self.hass.async_add_executor_job(lambda: sorted(folder.glob("*.yaml")) if folder.is_dir() else [])
        for file in files:
            path = f"{FOLDER}/{ext_id}/{file.name}"
            if path in in_use:
                continue
            # the automations just removed let go of it a moment later
            for _ in range(20):
                if not set(automations_with_blueprint(self.hass, path)) & set(removed):
                    break
                await asyncio.sleep(0.1)
            try:
                await async_get_blueprints(self.hass).async_remove_blueprint(path)
            except (BlueprintException, OSError) as err:
                _LOGGER.info("Keeping blueprint %s: %s", path, err)  # someone's own automation uses it
        await self.hass.async_add_executor_job(lambda: folder.is_dir() and not any(folder.iterdir()) and folder.rmdir())

    async def async_sweep(self, keep: set[str]) -> None:
        """Removes the automations and blueprints of extensions that are gone (licence removed or
        revoked, a trial ended); those of extensions in ``keep`` stay."""
        if AUTOMATION not in self.hass.config.components:
            return
        try:
            configs = await self.hass.async_add_executor_job(self._read)
            folders = await self.hass.async_add_executor_job(
                lambda: {d.name for d in self.folder.iterdir() if d.is_dir()} if self.folder.is_dir() else set()
            )
            for ext_id in sorted(({a["ext"] for a in listed(configs)} | folders) - keep):
                if EXT_ID.match(ext_id):
                    removed = await self.async_remove(ext_id)
                    _LOGGER.info("Removed the automations and blueprints of %s (no longer installed): %s", ext_id, removed)
        except (BlueprintError, HomeAssistantError, OSError) as err:
            _LOGGER.warning("Could not tidy up the automations of removed extensions: %s", err)
