"""Automations from extensions' blueprints (plain pytest; automations.py has no Home Assistant imports)."""

import base64
import functools
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / f"custom_components/virtuhome_pro/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


auto = load("automations")
lic = load("licensing")

KEY = Ed25519PrivateKey.generate()
PUB = base64.b64encode(KEY.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
verify = functools.partial(lic.verify_bundle, public_key_b64=PUB)

GARAGE_YAML = "blueprint:\n  name: Garage left open\n  domain: automation\n"


def bundle(blueprints=None, code=b"export default {id:'security'};"):
    if blueprints is None:
        return code
    return code + b"\n" + auto.MARKER + base64.b64encode(json.dumps(blueprints).encode()) + b"\n"


def installed(data, ext_id="security", version="1.2.0", sign=True):
    """The extension as the manager stores it: with the checksum and signature from the licence server."""
    sha = hashlib.sha256(data).hexdigest()
    entry = {"id": ext_id, "name": "Security", "version": version, "file": f"{ext_id}-{version}.js"}
    if sign:
        entry |= {"sha256": sha, "sig": base64.b64encode(KEY.sign(f"virtuhome-ext:v1:{ext_id}:{version}:{sha}".encode())).decode()}
    return entry


# ---------------------------------------------------------------- only blueprints from a signed bundle


def test_blueprints_come_out_of_the_signed_bundle():
    data = bundle({"garage_open": GARAGE_YAML})
    assert auto.bundle_blueprints(data) == {"garage_open": GARAGE_YAML}
    assert auto.signed_blueprint(installed(data), data, "garage_open", verify) == GARAGE_YAML
    assert auto.bundle_blueprints(bundle()) == {}


def test_unsigned_or_changed_bundles_are_refused():
    data = bundle({"garage_open": GARAGE_YAML})
    # stored by an older VirtuHome, without the signature: refused until the next renewal stores it
    with pytest.raises(auto.BlueprintError, match="without its signature"):
        auto.signed_blueprint(installed(data, sign=False), data, "garage_open", verify)
    # a blueprint changed after signing
    changed = bundle({"garage_open": GARAGE_YAML + "  description: also unlocks the door\n"})
    with pytest.raises(auto.BlueprintError, match="signature"):
        auto.signed_blueprint(installed(data), changed, "garage_open", verify)
    # signed by another key
    other = Ed25519PrivateKey.generate()
    entry = installed(data) | {"sig": base64.b64encode(other.sign(b"anything")).decode()}
    with pytest.raises(auto.BlueprintError):
        auto.signed_blueprint(entry, data, "garage_open", verify)


def test_unknown_blueprints_are_refused():
    data = bundle({"garage_open": GARAGE_YAML})
    with pytest.raises(auto.BlueprintError, match="no blueprint 'washing_done'"):
        auto.signed_blueprint(installed(data), data, "washing_done", verify)
    for bad in ({"../escape": GARAGE_YAML}, {"ok": 3}, ["garage_open"], {"big": "x" * (auto.MAX_YAML + 1)}):
        with pytest.raises(auto.BlueprintError):
            auto.bundle_blueprints(bundle(bad))
    with pytest.raises(auto.BlueprintError):
        auto.bundle_blueprints(b"code\n" + auto.MARKER + b"not base64!")


def test_only_automation_blueprints():
    with pytest.raises(auto.BlueprintError):
        auto.describe({"name": "A script", "domain": "script"}, {})


# ---------------------------------------------------------------- inputs

INPUTS = auto.describe(
    {"name": "Garage left open", "description": "Tells you when the garage is open late.", "domain": "automation"},
    {
        "door": {"name": "Garage door", "selector": {"entity": {"filter": [{"domain": ["cover", "binary_sensor"]}]}}},
        "at": {"name": "Time", "selector": {"time": {}}, "default": "22:00:00"},
        "minutes": {"name": "Open for", "selector": {"number": {"min": 1, "max": 120}}, "default": 10},
        "notify": {"name": "Phone", "selector": {"device": {"integration": "mobile_app"}}},
        "message": {"name": "Message", "selector": {"text": {}}, "default": "The garage is open."},
        "phones": {"name": "Phones", "selector": {"entity": {"domain": "notify", "multiple": True}}, "default": []},
        "steps": {"name": "Then", "selector": {"action": {}}, "default": []},
    },
)["inputs"]
PHONE = "0123456789abcdef0123456789abcdef"
HOME = {"cover.garage", "binary_sensor.garage", "notify.kadir", PHONE}


def exists(kind, value):
    return value in HOME


def test_inputs_are_checked_against_the_blueprint():
    good = {"door": "cover.garage", "notify": PHONE, "at": "21:30", "phones": ["notify.kadir"]}
    assert auto.check_inputs(INPUTS, good, exists) == good
    assert INPUTS["at"] == {"name": "Time", "description": "", "selector": {"time": {}}, "required": False, "default": "22:00:00"}


@pytest.mark.parametrize("given, error", [
    ({"door": "cover.garage"}, "missing inputs: notify"),
    ({"door": "cover.garage", "notify": PHONE, "unlock": "lock.front"}, "no input 'unlock'"),
    ({"door": "light.garage", "notify": PHONE}, "needs one of binary_sensor, cover"),
    ({"door": "cover.shed", "notify": PHONE}, "isn't in Home Assistant"),
    ({"door": "cover.garage", "notify": "../../etc"}, "not a device id"),
    ({"door": "cover.garage", "notify": PHONE, "message": "{{ states('lock.front') }}"}, "templates"),
    ({"door": "cover.garage", "notify": PHONE, "minutes": 500}, "out of range"),
    ({"door": "cover.garage", "notify": PHONE, "minutes": True}, "not a number"),
    ({"door": "cover.garage", "notify": PHONE, "at": "25:00"}, "not a time"),
    ({"door": "cover.garage", "notify": PHONE, "phones": "notify.kadir"}, "a list is needed"),
    ({"door": "cover.garage", "notify": PHONE, "steps": [{"action": "lock.unlock"}]}, "action selector isn't supported"),
])
def test_bad_inputs_are_refused(given, error):
    with pytest.raises(auto.BlueprintError, match=error):
        auto.check_inputs(INPUTS, given, exists)


# ---------------------------------------------------------------- adding, listing and removing

USERS_OWN = [{"id": "1700000000000", "alias": "Morning lights", "triggers": [], "actions": []}]


def test_add_list_and_remove():
    path = auto.blueprint_path("security", "garage_open")
    config = auto.new_automation("virtuhome-security-0a1b2c3d4e5f", "Garage left open", "Added by VirtuHome.", path,
                                 {"door": "cover.garage", "notify": PHONE})
    assert config == {
        "id": "virtuhome-security-0a1b2c3d4e5f", "alias": "Garage left open", "description": "Added by VirtuHome.",
        "use_blueprint": {"path": "virtuhome/security/garage_open.yaml", "input": {"door": "cover.garage", "notify": PHONE}},
    }
    wall = auto.new_automation("virtuhome-wall_tablet-ffffffffffff", "Dim at night", "", "virtuhome/wall_tablet/dim.yaml", {})
    configs = [*USERS_OWN, config, wall]

    assert auto.listed(configs) == [
        {"id": config["id"], "ext": "security", "alias": "Garage left open", "blueprint": "garage_open"},
        {"id": wall["id"], "ext": "wall_tablet", "alias": "Dim at night", "blueprint": "dim"},
    ]
    assert [a["id"] for a in auto.listed(configs, "security")] == [config["id"]]
    assert auto.blueprints_in_use(configs) == {path, "virtuhome/wall_tablet/dim.yaml"}

    # an extension removes only its own, and never anyone else's
    assert auto.remove_from(configs, "security", {USERS_OWN[0]["id"], wall["id"]}) == (configs, [])
    kept, removed = auto.remove_from(configs, "security", {config["id"]})
    assert (kept, removed) == ([*USERS_OWN, wall], [config["id"]])
    # all of an extension's go with it; the user's own automations stay
    assert auto.remove_from(configs, "wall_tablet")[0] == [*USERS_OWN, config]
    # taken over in the automation editor (no blueprint any more): still found by its id
    taken = {"id": config["id"], "alias": "Garage", "triggers": [], "actions": []}
    assert auto.listed([taken]) == [{"id": config["id"], "ext": "security", "alias": "Garage", "blueprint": None}]


def test_owner_needs_the_tag():
    assert auto.owner({"id": "virtuhome-security-0a1b"}) == "security"
    for other in ({"id": "virtuhome"}, {"id": "virtuhome-security"}, {"id": "1700"}, {"alias": "no id"}, "text"):
        assert auto.owner(other) is None


def test_notify_targets():
    config = {
        "triggers": [{"trigger": "state", "entity_id": "cover.garage", "to": "open", "action": "notify.not_this_one"}],
        "actions": [
            {"action": "notify.mobile_app_kadir", "data": {"message": "Garage open"}},
            {"choose": [{"conditions": [], "sequence": [{"service": "notify.family"}]}]},
            {"action": "notify.send_message", "target": {"entity_id": "notify.kitchen_speaker"}},
            {"domain": "mobile_app", "type": "notify", "device_id": PHONE, "message": "Garage open"},
            {"action": "notify.mobile_app_kadir", "data": {"message": "Still open"}},
            {"action": "light.turn_on"},
        ],
    }
    assert auto.notify_targets(config) == [
        {"service": "notify.mobile_app_kadir"},
        {"service": "notify.family"},
        {"service": "notify.send_message", "entity_id": "notify.kitchen_speaker"},
        {"device_id": PHONE},
    ]
