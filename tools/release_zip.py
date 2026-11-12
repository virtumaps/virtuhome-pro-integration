"""Builds the zip that HACS installs from each release, and attaches it to releases.

hacs.json has `zip_release` and `filename`, so HACS downloads that file from the release it installs
and unpacks it into custom_components/<domain>/. The zip therefore holds what that folder holds at
the release's tag, at its root (no folder around it). The download count HACS shows is this file's.

The zip is made from the tag's files as git stores them (what `git archive <tag>:<folder>` gives),
with the commit's time on every file, so the same tag makes the same bytes on any computer. That
lets a release's zip be checked against its tag by the checksum GitHub keeps for it, without
downloading it (which would count as a download).

    python3 tools/release_zip.py build <tag or commit> [--out DIR]
        build the zip from git and check it
    python3 tools/release_zip.py check <zip> <tag or commit>
        check a zip: the same files as the tag's custom_components/<domain>/, at its root
    python3 tools/release_zip.py release <tag> --target <commit> --notes-file <file> [--title <title>]
        publish a release with the zip attached (gh uploads it before the release is published)
    python3 tools/release_zip.py ensure <tag>
        check a published release's zip, or attach it if it is missing (the Release zip workflow)
    python3 tools/release_zip.py backfill [<tag> ...] [--upload] [--out DIR]
        build the zips of earlier releases (every vX.Y.Z tag by default) and check them; --upload
        attaches each one its release is missing, and checks the ones already there

Uses only Python's standard library, git and, to talk to GitHub, the gh CLI.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

REPO = "virtumaps/virtuhome-pro-integration"
DOMAIN = "virtuhome_pro"
ZIP = f"{DOMAIN}.zip"
FOLDER = f"custom_components/{DOMAIN}"
TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
# what Home Assistant's Marketplace refuses to unpack (marketplace/const.py)
MAX_BYTES = 100 * 1024 * 1024
MAX_FILES = 50_000

ROOT = Path(__file__).resolve().parents[1]


class Problem(Exception):
    pass


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def git_blob(sha: str) -> bytes:
    return subprocess.run(["git", "cat-file", "blob", sha], cwd=ROOT, check=True, capture_output=True).stdout


def gh(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    repo = [] if args[0] == "api" else ["--repo", REPO]
    return subprocess.run(["gh", *args, *repo], cwd=ROOT, check=check, capture_output=True, text=True)


def commit_of(ref: str) -> str:
    try:
        return git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    except subprocess.CalledProcessError:
        raise Problem(f"{ref} is not a tag or commit here (git fetch --tags?)") from None


def version_of(tag: str) -> str:
    if not TAG.match(tag):
        raise Problem(f"{tag} is not a release tag like v1.2.3")
    return tag[1:]


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def tree(commit: str) -> dict:
    """The tag's custom_components/<domain>/ as {path inside it: (git file mode, git blob id)}."""
    try:
        listing = git("ls-tree", "-r", "-z", f"{commit}:{FOLDER}")
    except subprocess.CalledProcessError:
        raise Problem(f"{commit[:12]} has no {FOLDER}/") from None
    files = {}
    for entry in filter(None, listing.split("\0")):
        meta, path = entry.split("\t", 1)
        mode, kind, sha = meta.split()
        if kind != "blob" or mode not in ("100644", "100755"):
            raise Problem(f"{FOLDER}/{path} is not a plain file (git mode {mode}), which HACS can't install")
        files[path] = (mode, sha)
    return files


def expected_files(commit: str) -> dict:
    """The tag's custom_components/<domain>/ as {path inside it: git blob id}."""
    return {path: sha for path, (_mode, sha) in tree(commit).items()}


def check(zip_path: Path, ref: str, version: str = None) -> int:
    """Checks the zip against ref; returns how many files it holds. Raises Problem when it differs."""
    commit = commit_of(ref)
    expected = expected_files(commit)
    problems = []
    actual = {}
    try:
        archive = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        raise Problem(f"{zip_path} is not a zip") from None
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES or sum(i.file_size for i in infos) > MAX_BYTES:
            problems.append("bigger than Home Assistant unpacks (100 MB, 50,000 files)")
        for info in infos:
            name = info.filename
            parts = PurePosixPath(name).parts
            if name.startswith("/") or "\\" in name or ".." in parts:
                problems.append(f"unsafe path {name}")
                continue
            if info.is_dir():
                continue
            if name in actual:
                problems.append(f"twice in the zip: {name}")
            actual[name] = blob_sha(archive.read(info))
        manifest = json.loads(archive.read("manifest.json")) if "manifest.json" in actual else None
    if manifest is None:
        problems.append("no manifest.json at the zip's root")
    else:
        if manifest.get("domain") != DOMAIN:
            problems.append(f"manifest.json domain is {manifest.get('domain')!r}, not {DOMAIN!r}")
        if version and manifest.get("version") != version:
            problems.append(f"manifest.json version is {manifest.get('version')!r}, not {version!r}")
    for path in sorted(expected.keys() - actual.keys()):
        problems.append(f"missing {path}")
    for path in sorted(actual.keys() - expected.keys()):
        problems.append(f"not in the tag: {path}")
    for path in sorted(expected.keys() & actual.keys()):
        if expected[path] != actual[path]:
            problems.append(f"differs from the tag: {path}")
    if problems:
        shown = problems[:20] + ([f"… and {len(problems) - 20} more"] if len(problems) > 20 else [])
        raise Problem(f"{zip_path} is not {ref}'s {FOLDER}/:\n  " + "\n  ".join(shown))
    return len(actual)


def build(ref: str, out_dir: Path, version: str = None) -> Path:
    commit = commit_of(ref)
    files = tree(commit)
    # the commit's time, in UTC, as git archive uses for a commit (zip can't go before 1980)
    stamp = time.gmtime(max(int(git("log", "-1", "--format=%ct", commit)), 315532800))[:6]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / ZIP
    path.unlink(missing_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name in sorted(files):
            mode, sha = files[name]
            info = zipfile.ZipInfo(name, stamp)
            info.create_system = 3  # unix, so the file mode below counts
            info.external_attr = (0o100755 if mode == "100755" else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, git_blob(sha), compresslevel=9)
    count = check(path, commit, version)
    print(f"{path}: {count} files, {path.stat().st_size} bytes, {ref} ({commit[:12]}), {sha256_of(path)}")
    return path


def sha256_of(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def release_assets(tag: str):
    """The release's assets as {name: GitHub's checksum or None}, or None when tag has no release."""
    view = gh("release", "view", tag, "--json", "assets", check=False)
    if view.returncode != 0:
        if "release not found" in view.stderr.lower():
            return None
        raise Problem(f"gh release view {tag}: {view.stderr.strip()}")
    return {asset["name"]: asset.get("digest") or None for asset in json.loads(view.stdout)["assets"]}


def ensure(tag: str) -> str:
    """Checks the zip of tag's release, attaching it first when it is missing."""
    version = version_of(tag)
    assets = release_assets(tag)
    if assets is None:
        raise Problem(f"there is no release for {tag}")
    with tempfile.TemporaryDirectory() as tmp:
        built = build(tag, Path(tmp) / "built", version)
        attached = ZIP not in assets
        if attached:
            gh("release", "upload", tag, str(built))
            assets = release_assets(tag) or {}
        if assets.get(ZIP) == sha256_of(built):
            how = "the same bytes as the tag's zip"
        else:
            # built differently (or GitHub has no checksum for it): compare what is in it, which
            # downloads it once
            gh("release", "download", tag, "--pattern", ZIP, "--dir", str(Path(tmp) / "release"))
            check(Path(tmp) / "release" / ZIP, tag, version)
            how = "the same files as the tag (downloaded to compare)"
    result = f"{tag}: {'attached' if attached else 'has'} {ZIP}, {how}"
    print(result)
    return result


def release(tag: str, target: str, notes: Path, title: str = None) -> None:
    version = version_of(tag)
    if not notes.is_file():
        raise Problem(f"no notes file {notes}")
    commit = commit_of(target)
    at_target = json.loads(git("show", f"{commit}:{FOLDER}/manifest.json")).get("version")
    if at_target != version:
        raise Problem(f"manifest.json at {commit[:12]} is version {at_target}, not {version}")
    if git("tag", "--list", tag) and commit_of(tag) != commit:
        raise Problem(f"the tag {tag} here is not {commit[:12]}")
    # a tag already on GitHub wins over --target, so it has to be the same commit
    remote = dict(line.split("\t")[::-1] for line in git("ls-remote", "--tags", "origin", tag).splitlines())
    on_github = remote.get(f"refs/tags/{tag}^{{}}") or remote.get(f"refs/tags/{tag}")
    if on_github and on_github != commit:
        raise Problem(f"the tag {tag} on GitHub is {on_github[:12]}, not {commit[:12]}")
    if gh("api", f"repos/{REPO}/commits/{commit}", "--silent", check=False).returncode != 0:
        raise Problem(f"{commit[:12]} is not on GitHub yet: push it (merge the release pull request) first")
    if release_assets(tag) is not None:
        raise Problem(f"{tag} already has a release: use `ensure {tag}` to check its zip")
    with tempfile.TemporaryDirectory() as tmp:
        path = build(commit, Path(tmp), version)
        # with a file to attach, gh makes a draft, uploads it, then publishes: the release is never
        # out without its zip (if an upload fails, gh deletes the draft again)
        create = gh("release", "create", tag, str(path), "--target", commit, "--title", title or version,
                    "--notes-file", str(notes), check=False)
        if create.returncode != 0:
            raise Problem(f"gh release create failed: {create.stderr.strip()}")
        print(create.stdout.strip())
    ensure(tag)


def all_tags() -> list:
    tags = [t for t in git("tag", "--list", "v*").split() if TAG.match(t)]
    return sorted(tags, key=lambda t: tuple(int(n) for n in TAG.match(t).groups()))


def backfill(tags: list, upload: bool, out_dir: Path) -> int:
    failed = 0
    for tag in tags or all_tags():
        try:
            if upload:
                ensure(tag)
            else:
                build(tag, out_dir / tag, version_of(tag))
        except (Problem, subprocess.CalledProcessError) as error:
            failed += 1
            detail = error.stderr if isinstance(error, subprocess.CalledProcessError) else error
            print(f"{tag}: {str(detail).strip()}", file=sys.stderr)
    return failed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("build")
    p.add_argument("ref")
    p.add_argument("--out", type=Path, default=ROOT / "tools/out")
    p = sub.add_parser("check")
    p.add_argument("zip", type=Path)
    p.add_argument("ref")
    p = sub.add_parser("release")
    p.add_argument("tag")
    p.add_argument("--target", required=True, help="the release commit (a tag, branch or SHA here)")
    p.add_argument("--notes-file", required=True, type=Path)
    p.add_argument("--title")
    p = sub.add_parser("ensure")
    p.add_argument("tag")
    p = sub.add_parser("backfill")
    p.add_argument("tags", nargs="*")
    p.add_argument("--upload", action="store_true")
    p.add_argument("--out", type=Path, default=ROOT / "tools/out/zips")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            build(args.ref, args.out, version_of(args.ref) if TAG.match(args.ref) else None)
        elif args.command == "check":
            count = check(args.zip, args.ref, version_of(args.ref) if TAG.match(args.ref) else None)
            print(f"{args.zip}: {count} files, the same as {args.ref}'s {FOLDER}/")
        elif args.command == "release":
            release(args.tag, args.target, args.notes_file, args.title)
        elif args.command == "ensure":
            ensure(args.tag)
        elif args.command == "backfill":
            return 1 if backfill(args.tags, args.upload, args.out) else 0
    except Problem as problem:
        print(f"error: {problem}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(f"error: {' '.join(error.cmd)} failed: {str(error.stderr or '').strip()}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
