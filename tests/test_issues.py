"""Which repair issues apply (plain pytest; issues.py has no Home Assistant imports)."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1] / "custom_components/virtuhome_pro"
spec = importlib.util.spec_from_file_location("issues", ROOT / "issues.py")
issues = importlib.util.module_from_spec(spec)
spec.loader.exec_module(issues)

NOW = 2_000_000_000


def test_nothing_wrong():
    assert issues.found_issues({"status": "none", "key_hint": None}, NOW) == {}
    assert issues.found_issues(None, NOW) == {}


def test_licence_not_renewed_for_a_month():
    licence = {"status": "active", "key_hint": "VH-1…ABCD", "checked": NOW - 31 * 86400, "error": "could not reach the licence server"}
    assert issues.found_issues(licence, NOW) == {"licence_not_renewed": {"days": "31", "error": "could not reach the licence server"}}
    assert issues.found_issues({**licence, "checked": NOW - 5 * 86400}, NOW) == {}
    # trials alone have no key to renew
    assert issues.found_issues({**licence, "key_hint": None, "status": "none"}, NOW) == {}


def test_every_text_in_every_language():
    english = json.loads((ROOT / "strings.json").read_text())
    for lang in ("en", "de", "nl"):
        texts = json.loads((ROOT / "translations" / f"{lang}.json").read_text())
        assert set(texts["issues"]) == set(issues.ISSUE_IDS) | {"virtuhome_too_old"}, lang
        assert texts.keys() == english.keys(), lang
        assert texts["config"]["step"].keys() == english["config"]["step"].keys(), lang
