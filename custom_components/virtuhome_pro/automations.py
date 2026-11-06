"""Automations that extensions add from blueprints (no Home Assistant imports: testable alone).

Extensions never run code inside Home Assistant. An extension's bundle can carry blueprints, plain
YAML in its last line ``//# virtuhome-blueprints=<base64 of JSON {"<id>": "<yaml>"}>``, so the
bundle's checksum and signature cover them like the rest of it. When the user agrees, the
integration writes one to ``blueprints/automation/virtuhome/<extension>/<id>.yaml`` and adds an
automation that uses it to ``automations.yaml``, as Home Assistant's automation editor does
(automation_store.py). The browser only names the blueprint and gives its inputs, never YAML.
Automations are found again by their id, ``virtuhome-<extension>-<hex>``.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from collections.abc import Callable
from typing import Any

MARKER = b"//# virtuhome-blueprints="
FOLDER = "virtuhome"  # under blueprints/automation/
ID_PREFIX = "virtuhome-"

BLUEPRINT_ID = re.compile(r"^[a-z0-9_]{1,40}$")
EXT_ID = re.compile(r"^[a-z0-9_]{1,40}$")
MAX_BLUEPRINTS = 20
MAX_YAML = 64 * 1024
MAX_ITEMS = 50
ENTITY_ID = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
DEVICE_ID = re.compile(r"^[0-9a-f]{32}$")
AREA_ID = re.compile(r"^[a-z0-9_]{1,64}$")
TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")
TEMPLATE = re.compile(r"\{\{|\{%|\{#")


class BlueprintError(Exception):
    """A blueprint or its inputs that can't be used."""


def bundle_blueprints(bundle: bytes) -> dict[str, str]:
    """The blueprints in a bundle (id -> YAML text). Check the bundle's signature first."""
    lines = [line for line in bundle.rstrip().split(b"\n") if line.startswith(MARKER)]
    if not lines:
        return {}
    try:
        data = json.loads(base64.b64decode(lines[-1][len(MARKER):].strip(), validate=True))
    except (binascii.Error, ValueError) as err:
        raise BlueprintError("the extension's blueprints can't be read") from err
    if not isinstance(data, dict) or len(data) > MAX_BLUEPRINTS:
        raise BlueprintError("the extension's blueprints can't be read")
    for bp_id, text in data.items():
        if not BLUEPRINT_ID.match(bp_id) or not isinstance(text, str) or len(text) > MAX_YAML:
            raise BlueprintError(f"the extension's blueprint {bp_id!r} can't be used")
    return data


def signed_blueprint(ext: dict[str, Any], bundle: bytes, bp_id: str, verify: Callable[..., None]) -> str:
    """One blueprint's YAML from an installed extension's bundle, once the bundle matches the checksum
    and signature stored with it (``verify`` is licensing.verify_bundle)."""
    if not ext.get("sha256") or not ext.get("sig"):
        raise BlueprintError(f"{ext['id']} was stored without its signature: Check for updates in Extras first")
    try:
        verify(ext["id"], ext["version"], bundle, ext["sha256"], ext["sig"])
    except Exception as err:  # noqa: BLE001 - whatever the reason, it isn't the bundle VirtuMaps signed
        raise BlueprintError(f"{ext['id']} doesn't match its signature") from err
    text = bundle_blueprints(bundle).get(bp_id)
    if text is None:
        raise BlueprintError(f"{ext['id']} has no blueprint {bp_id!r}")
    return text


def blueprint_path(ext_id: str, bp_id: str) -> str:
    """Where the blueprint goes, relative to blueprints/automation/ (as use_blueprint names it)."""
    return f"{FOLDER}/{ext_id}/{bp_id}.yaml"


def owner(config: Any) -> str | None:
    """The extension that added an automation (from its id), or None for anyone else's."""
    auto_id = str(config.get("id", "")) if isinstance(config, dict) else ""
    if not auto_id.startswith(ID_PREFIX):
        return None
    ext_id, _, rest = auto_id[len(ID_PREFIX):].rpartition("-")
    return ext_id if EXT_ID.match(ext_id) and rest else None


def listed(configs: list[Any], ext_id: str | None = None) -> list[dict[str, Any]]:
    """The automations extensions added (one extension's with ext_id), from automations.yaml."""
    out = []
    for config in configs:
        if (ext := owner(config)) is None or (ext_id is not None and ext != ext_id):
            continue
        path = str((config.get("use_blueprint") or {}).get("path", ""))
        prefix = f"{FOLDER}/{ext}/"
        out.append({
            "id": str(config["id"]),
            "ext": ext,
            "alias": config.get("alias"),
            # gone when someone took it over in the automation editor
            "blueprint": path[len(prefix):-len(".yaml")] if path.startswith(prefix) and path.endswith(".yaml") else None,
        })
    return out


def remove_from(configs: list[Any], ext_id: str, ids: set[str] | None = None) -> tuple[list[Any], list[str]]:
    """automations.yaml without the extension's automations (those in ids, or all): (kept, removed ids)."""
    gone = {a["id"] for a in listed(configs, ext_id) if ids is None or a["id"] in ids}
    kept = [c for c in configs if not (owner(c) == ext_id and str(c.get("id")) in gone)]
    return kept, sorted(gone)


def blueprints_in_use(configs: list[Any]) -> set[str]:
    """The blueprint paths automations.yaml uses (anyone's automations)."""
    return {str(c["use_blueprint"].get("path")) for c in configs if isinstance(c, dict) and isinstance(c.get("use_blueprint"), dict)}


def new_automation(auto_id: str, alias: str, description: str, path: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """The automations.yaml entry: the blueprint and its inputs."""
    config: dict[str, Any] = {"id": auto_id, "alias": alias}
    if description:
        config["description"] = description
    config["use_blueprint"] = {"path": path, "input": inputs}
    return config


def describe(metadata: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    """Name, description and inputs of a parsed blueprint (Blueprint.metadata, Blueprint.inputs)."""
    if metadata.get("domain") != "automation":
        raise BlueprintError("only automation blueprints can be added")
    out = {}
    for key, spec in inputs.items():
        spec = spec if isinstance(spec, dict) else {}
        out[key] = {
            "name": str(spec.get("name") or key),
            "description": str(spec.get("description") or ""),
            "selector": spec.get("selector") or {"text": {}},
            "required": "default" not in spec,
        }
        if "default" in spec:
            out[key]["default"] = spec["default"]
    return {"name": str(metadata.get("name", "")), "description": str(metadata.get("description") or ""), "inputs": out}


def check_inputs(
    inputs: dict[str, Any], given: dict[str, Any], exists: Callable[[str, str], bool] = lambda kind, value: True
) -> dict[str, Any]:
    """The given inputs, checked against the blueprint's (describe()["inputs"]) and its selectors.

    Values are plain data: entity, device and area ids that exist, numbers, times, choices and text
    without templates. ``exists(kind, id)`` says whether an entity, device or area is there."""
    out = {}
    for key, value in given.items():
        if key not in inputs:
            raise BlueprintError(f"the blueprint has no input {key!r}")
        selector = inputs[key]["selector"]
        kind, options = next(iter(selector.items())) if isinstance(selector, dict) and selector else ("text", {})
        options = options if isinstance(options, dict) else {}
        if options.get("multiple"):
            if not isinstance(value, list) or len(value) > MAX_ITEMS:
                raise BlueprintError(f"{key}: a list is needed")
            out[key] = [_value(key, kind, options, v, exists) for v in value]
        else:
            out[key] = _value(key, kind, options, value, exists)
    missing = sorted(k for k, spec in inputs.items() if spec["required"] and k not in out)
    if missing:
        raise BlueprintError(f"missing inputs: {', '.join(missing)}")
    return out


def _domains(options: dict[str, Any]) -> set[str]:
    found: list[Any] = [options.get("domain")]
    filters = options.get("filter")
    for f in filters if isinstance(filters, list) else [filters]:
        if isinstance(f, dict):
            found.append(f.get("domain"))
    return {d for item in found for d in (item if isinstance(item, list) else [item]) if isinstance(d, str)}


def _value(key: str, kind: str, options: dict[str, Any], value: Any, exists: Callable[[str, str], bool]) -> Any:
    def bad(what: str) -> BlueprintError:
        return BlueprintError(f"{key}: {what}")

    if isinstance(value, str) and TEMPLATE.search(value):
        raise bad("templates aren't allowed")
    if kind in ("entity", "device", "area"):
        pattern = {"entity": ENTITY_ID, "device": DEVICE_ID, "area": AREA_ID}[kind]
        if not isinstance(value, str) or not pattern.match(value):
            raise bad(f"not an {kind} id" if kind in ("entity", "area") else "not a device id")
        domains = _domains(options) if kind == "entity" else set()
        if domains and value.split(".")[0] not in domains:
            raise bad(f"needs one of {', '.join(sorted(domains))}")
        if not exists(kind, value):
            raise bad(f"{value} isn't in Home Assistant")
        return value
    if kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise bad("not a number")
        low, high = options.get("min"), options.get("max")
        if (isinstance(low, (int, float)) and value < low) or (isinstance(high, (int, float)) and value > high):
            raise bad("out of range")
        return value
    if kind == "boolean":
        if not isinstance(value, bool):
            raise bad("not true or false")
        return value
    if kind == "time":
        if not isinstance(value, str) or not TIME.match(value):
            raise bad("not a time (HH:MM)")
        return value
    if kind == "duration":
        units = ("days", "hours", "minutes", "seconds")
        if not isinstance(value, dict) or not value or any(
            u not in units or isinstance(n, bool) or not isinstance(n, (int, float)) or n < 0 for u, n in value.items()
        ):
            raise bad("not a duration")
        return value
    if kind == "select":
        choices = [o.get("value") if isinstance(o, dict) else o for o in options.get("options") or []]
        if value not in choices:
            raise bad("not one of the choices")
        return value
    if kind == "text":
        if not isinstance(value, str) or len(value) > (1000 if options.get("multiline") else 255):
            raise bad("not a short text")
        return value
    raise bad(f"the {kind} selector isn't supported")


def notify_targets(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Where an automation's notifications go (its inputs filled in): notify services and the
    devices of mobile_app notify actions."""
    found: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            call = node.get("action", node.get("service"))
            if isinstance(call, str) and call.startswith("notify."):
                target = node.get("target")
                entities = target.get("entity_id") if isinstance(target, dict) else None
                item: dict[str, Any] = {"service": call}
                if entities:
                    item["entity_id"] = entities
                found.append(item)
            elif node.get("domain") == "mobile_app" and node.get("type") == "notify" and node.get("device_id"):
                found.append({"device_id": node["device_id"]})
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk([config.get(k) for k in ("actions", "action")])
    unique: list[dict[str, Any]] = []
    for item in found:
        if item not in unique:
            unique.append(item)
    return unique
