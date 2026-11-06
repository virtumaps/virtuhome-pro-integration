"""What "Download diagnostics" puts in the file (no Home Assistant imports: testable alone).

Never the licence key, token, activation id or installation hash: the licence part is built from a
short list of safe fields, and diagnostics.py also runs Home Assistant's redaction over the result.
"""

from __future__ import annotations

from typing import Any

# blanked by Home Assistant's async_redact_data wherever they appear in the report
TO_REDACT = {"key", "key_hint", "token", "activation", "act", "instance", "inst"}


def licence_summary(summary: dict[str, Any] | None, loaded: list[dict[str, Any]]) -> dict[str, Any]:
    """The licence state and each extension: from ExtensionManager.summary() and .extensions()."""
    if summary is None:
        return {"status": "unavailable"}
    loaded_ids = {e.get("id") for e in loaded}
    return {
        "status": summary.get("status"),
        "kind": summary.get("kind"),
        "error": summary.get("error"),
        "server": summary.get("server"),
        "key_entered": bool(summary.get("key_hint")),
        "last_check": summary.get("checked"),
        "extensions": [
            {"id": e.get("id"), "version": e.get("version"), "loaded": e.get("id") in loaded_ids}
            for e in summary.get("extensions") or []
        ],
        "trials": [
            {"id": e.get("id"), "status": e.get("status"), "loaded": e.get("id") in loaded_ids}
            for e in summary.get("trials") or []
        ],
    }


def build_report(*, version: str, core_version: str | None, ha_version: str, options: dict[str, Any],
                 summary: dict[str, Any] | None, loaded: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "virtuhome_pro_version": version,
        "virtuhome_version": core_version,
        "home_assistant_version": ha_version,
        "options": {k: v for k, v in options.items() if k not in TO_REDACT},
        "licence": licence_summary(summary, loaded),
    }
