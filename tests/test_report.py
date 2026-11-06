"""The diagnostics report (plain pytest; report.py has no Home Assistant imports)."""

import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("report", Path(__file__).parents[1] / "custom_components/virtuhome_pro/report.py")
rep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rep)

KEY = "VH-TEST-KEY-0000-QW7Z"
TOKEN = "vhl1.eyJpbnN0IjoiYWJjIn0.c2lnbmF0dXJl"
ACTIVATION = "act_7f3c9e"
INSTANCE = "0f1e2d3c4b5a69788796a5b4c3d2e1f0"


class FakeManager:
    """ExtensionManager with a real-looking licence in its stored data."""

    data = {"key": KEY, "activation": ACTIVATION, "token": TOKEN, "checked": 1792279060.9,
            "extensions": [{"id": "security", "name": "Security", "version": "1.0.2", "file": "security-1.0.2.js"},
                           {"id": "energy", "name": "Energy", "version": "1.0.0", "file": "energy-1.0.0.js"}]}
    instance = INSTANCE

    def summary(self):
        return {"status": "active", "kind": "paid", "error": None, "key_hint": f"{KEY[:4]}…{KEY[-4:]}",
                "extensions": [{k: e[k] for k in ("id", "name", "version")} for e in self.data["extensions"]],
                "checked": self.data["checked"], "server": "https://licence.example"}

    def extensions(self):
        return [{"id": "security", "name": "Security", "version": "1.0.2", "url": "/virtuhome_ext/security-1.0.2.js"}]


def report():
    manager = FakeManager()
    return rep.build_report(
        version="1.0.0", core_version="0.18.0", ha_version="2026.10.2",
        options={"licence_server": "https://licence.example", "key": KEY},
        summary=manager.summary(), loaded=manager.extensions(),
    )


def test_licence_and_extensions():
    lic = report()["licence"]
    assert lic["status"] == "active" and lic["kind"] == "paid" and lic["key_entered"]
    assert lic["extensions"] == [
        {"id": "security", "version": "1.0.2", "loaded": True},
        {"id": "energy", "version": "1.0.0", "loaded": False},
    ]


def test_no_secrets_anywhere():
    text = json.dumps(report(), ensure_ascii=False)
    for secret in (KEY, KEY[-4:], TOKEN, ACTIVATION, INSTANCE):
        assert secret not in text
    assert {"key", "token", "activation", "instance"} <= rep.TO_REDACT
    assert report()["options"] == {"licence_server": "https://licence.example"}


def test_not_loaded():
    out = rep.build_report(version="1.0.0", core_version=None, ha_version="2026.10.2", options={}, summary=None, loaded=[])
    assert out["licence"] == {"status": "unavailable"} and out["virtuhome_version"] is None
