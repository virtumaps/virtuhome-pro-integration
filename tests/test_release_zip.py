"""The zip HACS installs from each release (tools/release_zip.py): built from git, the integration's
files at its root, the same bytes every time, and the checks that refuse anything else."""

import importlib.util
import json
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("release_zip", ROOT / "tools/release_zip.py")
release_zip = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_zip)


def test_hacs_json_names_the_zip():
    hacs = json.loads((ROOT / "hacs.json").read_text())
    manifest = json.loads((ROOT / release_zip.FOLDER / "manifest.json").read_text())
    assert hacs.get("zip_release") is True
    assert hacs.get("filename") == release_zip.ZIP == f"{manifest['domain']}.zip"


def test_zip_holds_the_integration_at_its_root(tmp_path):
    path = release_zip.build("HEAD", tmp_path)
    names = zipfile.ZipFile(path).namelist()
    assert path.name == release_zip.ZIP
    assert "manifest.json" in names and "__init__.py" in names
    assert not [n for n in names if n.startswith("custom_components/")]
    tracked = subprocess.run(["git", "ls-files", release_zip.FOLDER], cwd=ROOT, capture_output=True, text=True, check=True)
    files = [n for n in names if not n.endswith("/")]
    assert sorted(files) == sorted(f[len(release_zip.FOLDER) + 1 :] for f in tracked.stdout.split())


def test_the_same_commit_makes_the_same_bytes(tmp_path):
    first = release_zip.build("HEAD", tmp_path / "a")
    assert release_zip.sha256_of(first) == release_zip.sha256_of(release_zip.build("HEAD", tmp_path / "b"))


def test_check_refuses_a_zip_with_a_folder_around_it(tmp_path):
    path = tmp_path / release_zip.ZIP
    subprocess.run(["git", "archive", "--format=zip", "-o", str(path), "HEAD", release_zip.FOLDER], cwd=ROOT, check=True)
    with pytest.raises(release_zip.Problem, match="no manifest.json at the zip's root"):
        release_zip.check(path, "HEAD")


def test_check_refuses_a_changed_or_extra_file(tmp_path):
    built = zipfile.ZipFile(release_zip.build("HEAD", tmp_path))
    path = tmp_path / "changed.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for info in built.infolist():
            archive.writestr(info, b"# changed\n" if info.filename == "const.py" else built.read(info))
        archive.writestr("extra.py", "")
    with pytest.raises(release_zip.Problem) as error:
        release_zip.check(path, "HEAD")
    assert "differs from the tag: const.py" in str(error.value)
    assert "not in the tag: extra.py" in str(error.value)


def test_check_wants_the_tags_version(tmp_path):
    path = release_zip.build("HEAD", tmp_path)
    with pytest.raises(release_zip.Problem, match="manifest.json version"):
        release_zip.check(path, "HEAD", "0.0.0-not-this")
