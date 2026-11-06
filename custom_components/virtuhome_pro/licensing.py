"""Signatures of licence tokens and extension bundles (no Home Assistant imports: testable alone).

The licence server signs with an Ed25519 key; the integration only holds the public key.

Licence token: ``vhl1.<base64url payload JSON>.<base64url signature over the payload bytes>``
  payload: {"v": 1, "key": "<licence id>", "act": "<activation id>", "ext": ["wall_tablet", ...],
            "inst": "<installation hash>", "iat": <unix>, "exp": <unix>,
            "kind": "trial" | "paid" | "installer", "perpetual": <bool>, "ended": <unix>}
  ``exp`` is the renewal date (a trial's end). Perpetual licences (paid and installer ones unless
  ``perpetual`` says otherwise) keep what is installed: past ``exp``, or once the server marks one
  ``ended``, the stored bundles still load and only newer versions need a current token. Others (a
  trial) stop at ``exp``. Tokens issued before licences had a ``kind`` were all installer keys
  (activation ``installer-…``) or paid keys.

Extension bundle: the server publishes ``sha256`` of the file and a signature over
``virtuhome-ext:v1:<id>:<version>:<sha256 hex>``.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from typing import Any, NamedTuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# Public half of the VirtuHome licence signing key (tools/keygen in virtuhome-pro).
PUBLIC_KEY_B64 = "vDaOEr/I1gLJ9gcXxrEoLvhjpJZeUDZpu2QDJJL+d20="

TOKEN_PREFIX = "vhl1"

# kinds of licence whose installed versions keep working for good
PERPETUAL = ("paid", "installer")


class LicenceError(Exception):
    """A token or bundle that does not check out."""


def _b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _key(public_key_b64: str = PUBLIC_KEY_B64) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))


def installation_hash(instance_id: str) -> str:
    """A stable, anonymous id of this Home Assistant installation (the licence binds to it)."""
    return hashlib.sha256(f"virtuhome:{instance_id}".encode()).hexdigest()[:32]


def read_token(token: str, instance: str, *, public_key_b64: str = PUBLIC_KEY_B64) -> dict[str, Any]:
    """Checks the signature and the installation (not the dates); returns the payload."""
    try:
        prefix, payload_b64, sig_b64 = token.split(".")
    except ValueError as err:
        raise LicenceError("malformed token") from err
    if prefix != TOKEN_PREFIX:
        raise LicenceError("unknown token format")
    payload_bytes = _b64url_decode(payload_b64)
    try:
        _key(public_key_b64).verify(_b64url_decode(sig_b64), payload_bytes)
    except InvalidSignature as err:
        raise LicenceError("bad signature") from err
    payload = json.loads(payload_bytes)
    if payload.get("inst") != instance:
        raise LicenceError("licence belongs to another installation")
    return payload


def verify_token(token: str, instance: str, *, now: float | None = None, public_key_b64: str = PUBLIC_KEY_B64) -> dict[str, Any]:
    """read_token, and refuses a token past its renewal date: a renewal brings a current one."""
    payload = read_token(token, instance, public_key_b64=public_key_b64)
    if payload.get("exp", 0) < (now if now is not None else time.time()):
        raise LicenceError("licence expired")
    return payload


class Licence(NamedTuple):
    """What a licence allows now."""

    kind: str  # trial | paid | installer (another: a kind this version doesn't know, treated like a trial)
    status: str  # active | lapsed (past renewal, still loads) | ended (marked ended, still loads) | expired
    ext: frozenset[str]
    exp: float

    @property
    def loads(self) -> bool:
        """The installed extensions it unlocks load."""
        return self.status != "expired"

    @property
    def updates(self) -> bool:
        """Newer versions may be downloaded."""
        return self.status == "active"


def licence_kind(payload: dict[str, Any]) -> str:
    kind = payload.get("kind")
    if kind is None:
        # before licences said their kind, the server only had installer keys and paid keys
        return "installer" if str(payload.get("act", "")).startswith("installer-") else "paid"
    return str(kind)


def licence_state(payload: dict[str, Any], *, now: float | None = None) -> Licence:
    now = time.time() if now is None else now
    kind = licence_kind(payload)
    perpetual = payload["perpetual"] if isinstance(payload.get("perpetual"), bool) else kind in PERPETUAL
    if payload.get("ended"):
        status = "ended" if perpetual else "expired"
    elif payload.get("exp", 0) >= now:
        status = "active"
    else:
        status = "lapsed" if perpetual else "expired"
    return Licence(kind, status, frozenset(payload.get("ext") or []), float(payload.get("exp", 0)))


def loadable(installed: list[dict[str, Any]], licence: Licence | None) -> list[dict[str, Any]]:
    """The installed extensions that load now."""
    if licence is None or not licence.loads:
        return []
    return [e for e in installed if e["id"] in licence.ext]


def to_keep(installed: list[dict[str, Any]], offered: list[dict[str, Any]], licence: Licence) -> list[dict[str, Any]]:
    """After a renewal: the versions the server offers while the licence gets updates, else the installed ones."""
    if licence.updates:
        return [e for e in offered if e["id"] in licence.ext]
    return loadable(installed, licence)


def with_trials(main: list[dict[str, Any]], trials: list[tuple[Licence | None, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
    """The extensions that load: the licence's, then those on a trial that hasn't ended (a bought one wins)."""
    out = list(main)
    ids = {e["id"] for e in out}
    for licence, entries in trials:
        if licence is None or licence.kind != "trial":
            continue
        for e in loadable(entries, licence):
            if e["id"] not in ids:
                ids.add(e["id"])
                out.append(e)
    return out


def licence_servers(option: str | None, default: str, old: str) -> list[str]:
    """Where the licence server is, in the order to try: an address set in the options alone, else
    our own address, then the first one (installs from before it still have that one stored)."""
    own = (option or "").strip().rstrip("/")
    if own and own not in (default, old):
        return [own]
    return [default, old]


def ends_licence(message: str) -> bool:
    """A renewal answer that ends the licence here (revoked, refunded, unknown key): all of it stops."""
    text = message.lower()
    return "revoked" in text or "refunded" in text or "not found" in text


def verify_bundle(ext_id: str, version: str, data: bytes, sha256_hex: str, sig_b64: str, *, public_key_b64: str = PUBLIC_KEY_B64) -> None:
    """Raises unless ``data`` is exactly the bundle the licence server signed."""
    digest = hashlib.sha256(data).hexdigest()
    if digest != sha256_hex:
        raise LicenceError(f"{ext_id} {version}: checksum mismatch")
    message = f"virtuhome-ext:v1:{ext_id}:{version}:{sha256_hex}".encode()
    try:
        _key(public_key_b64).verify(base64.b64decode(sig_b64), message)
    except InvalidSignature as err:
        raise LicenceError(f"{ext_id} {version}: bad signature") from err
