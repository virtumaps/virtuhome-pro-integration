"""Licence token and bundle checks (plain pytest; licensing.py has no Home Assistant imports)."""

import base64
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

spec = importlib.util.spec_from_file_location("licensing", Path(__file__).parents[1] / "custom_components/virtuhome_pro/licensing.py")
lic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lic)

KEY = Ed25519PrivateKey.generate()
PUB = base64.b64encode(KEY.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()


def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def token(payload: dict) -> str:
    data = json.dumps(payload).encode()
    return f"vhl1.{b64url(data)}.{b64url(KEY.sign(data))}"


INST = lic.installation_hash("home-1")


def test_valid_token():
    t = token({"v": 1, "ext": ["wall_tablet"], "inst": INST, "iat": 0, "exp": 2_000_000_000})
    assert lic.verify_token(t, INST, now=1_900_000_000, public_key_b64=PUB)["ext"] == ["wall_tablet"]


@pytest.mark.parametrize("case", ["other_install", "expired", "tampered", "foreign_key"])
def test_rejected_tokens(case):
    payload = {"v": 1, "ext": ["wall_tablet"], "inst": INST, "iat": 0, "exp": 2_000_000_000}
    t = token(payload)
    inst = INST
    now = 1_900_000_000
    pub = PUB
    if case == "other_install":
        inst = lic.installation_hash("home-2")
    elif case == "expired":
        now = 2_100_000_000
    elif case == "tampered":
        prefix, body, sig = t.split(".")
        body = b64url(json.dumps({**payload, "ext": ["energy"]}).encode())
        t = f"{prefix}.{body}.{sig}"
    else:
        other = Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        pub = base64.b64encode(other).decode()
    with pytest.raises(lic.LicenceError):
        lic.verify_token(t, inst, now=now, public_key_b64=pub)


def test_bundle_signature():
    data = b"export default {}"
    sha = hashlib.sha256(data).hexdigest()
    sig = base64.b64encode(KEY.sign(f"virtuhome-ext:v1:wall_tablet:1.0.0:{sha}".encode())).decode()
    lic.verify_bundle("wall_tablet", "1.0.0", data, sha, sig, public_key_b64=PUB)
    with pytest.raises(lic.LicenceError):
        lic.verify_bundle("wall_tablet", "1.0.0", data + b" ", sha, sig, public_key_b64=PUB)
    with pytest.raises(lic.LicenceError):
        lic.verify_bundle("wall_tablet", "1.0.1", data, sha, sig, public_key_b64=PUB)


# ---------------------------------------------------------------- what keeps working (perpetual licences)

NOW = 1_900_000_000
PAST = NOW - 86400  # the renewal date went by yesterday
SECURITY_1 = {"id": "security", "name": "Security", "version": "1.0.0", "file": "security-1.0.0.js"}
SECURITY_2 = {"id": "security", "name": "Security", "version": "1.1.0", "sha256": "ab", "sig": "cd"}


def state(**payload):
    """The licence a stored token holds, read as the integration reads it (signature checked)."""
    t = token({"v": 1, "ext": ["security"], "inst": INST, "iat": 0, "exp": PAST, **payload})
    return lic.licence_state(lic.read_token(t, INST, public_key_b64=PUB), now=NOW)


def test_expired_paid_licence_still_loads():
    paid = state(kind="paid")
    assert (paid.status, paid.loads, paid.updates) == ("lapsed", True, False)
    assert lic.loadable([SECURITY_1], paid) == [SECURITY_1]
    # a renewal brings a current token again, and with it new versions
    renewed = state(kind="paid", exp=NOW + 365 * 86400)
    assert renewed.updates and lic.to_keep([SECURITY_1], [SECURITY_2], renewed) == [SECURITY_2]


def test_ended_installer_licence_keeps_its_installed_versions():
    ended = state(kind="installer", ended=PAST, exp=NOW + 365 * 86400)
    assert (ended.status, ended.loads, ended.updates) == ("ended", True, False)
    assert lic.loadable([SECURITY_1], ended) == [SECURITY_1]
    # what the server offers is not downloaded: the installed version stays
    assert lic.to_keep([SECURITY_1], [SECURITY_2], ended) == [SECURITY_1]


def test_expired_trial_stops():
    trial = state(kind="trial")
    assert (trial.status, trial.loads) == ("expired", False)
    assert lic.loadable([SECURITY_1], trial) == []
    assert lic.loadable([SECURITY_1], state(kind="trial", exp=NOW + 86400)) == [SECURITY_1]
    # a kind this version doesn't know lasts only until its date, like a trial
    assert not state(kind="rental").loads
    # unless the token says it is perpetual; and the server can make any kind time-limited
    assert state(kind="rental", perpetual=True).loads
    assert not state(kind="paid", perpetual=False).loads


def test_revoked_licence_stops_at_the_next_renewal():
    paid = state(kind="paid")
    assert lic.loadable([SECURITY_1], paid) == [SECURITY_1]
    # the server's answers to a renewal: these end the licence here (the manager deletes what it unlocked)
    for answer in ("This licence was revoked", "Licence key not found", "This order was refunded"):
        assert lic.ends_licence(answer)
    # these don't: the installed versions keep working
    for answer in ("licence server answered 500", "could not reach the licence server", "licence expired"):
        assert not lic.ends_licence(answer)


def test_tokens_without_a_kind_are_perpetual():
    """Tokens the server issued before licences had a kind: installer keys and paid keys, both kept."""
    installer = state(act="installer-" + INST)
    paid = state(act="5f1c0d2e-activation")
    assert (installer.kind, installer.status, installer.loads) == ("installer", "lapsed", True)
    assert (paid.kind, paid.status, paid.loads) == ("paid", "lapsed", True)
    assert state(act="installer-" + INST, exp=NOW + 1).status == "active"


def test_read_token_ignores_dates_but_not_the_installation():
    t = token({"v": 1, "ext": [], "inst": INST, "iat": 0, "exp": PAST})
    assert lic.read_token(t, INST, public_key_b64=PUB)["exp"] == PAST
    with pytest.raises(lic.LicenceError):
        lic.read_token(t, lic.installation_hash("home-2"), public_key_b64=PUB)
    with pytest.raises(lic.LicenceError):
        lic.verify_token(t, INST, now=NOW, public_key_b64=PUB)


def trial_state(ext, status="active", kind="trial"):
    return lic.Licence(kind, status, frozenset(ext), 2_000_000_000)


def entry(ext_id, version="1.0.0"):
    return {"id": ext_id, "version": version, "file": f"{ext_id}-{version}.js"}


def test_trials_add_to_the_licence():
    main = [entry("energy", "1.2.0")]
    got = lic.with_trials(main, [(trial_state(["security"]), [entry("security")])])
    assert [e["id"] for e in got] == ["energy", "security"]


def test_a_bought_extension_wins_over_its_trial():
    main = [entry("energy", "1.2.0")]
    got = lic.with_trials(main, [(trial_state(["energy"]), [entry("energy", "1.1.0")])])
    assert got == main


def test_ended_or_broken_trials_load_nothing():
    trials = [
        (trial_state(["security"], "expired"), [entry("security")]),
        (None, [entry("household")]),
        # a token that isn't a trial can't sneak in through the trials
        (trial_state(["network"], "active", "installer"), [entry("network")]),
        (trial_state(["energy"]), [entry("wall_tablet")]),
    ]
    assert lic.with_trials([], trials) == []


NEW, OLD = "https://license.example", "https://old.example.workers.dev"


@pytest.mark.parametrize("option,expected", [
    (None, [NEW, OLD]),
    ("", [NEW, OLD]),
    # what the options form saved before there was our own address
    (OLD, [NEW, OLD]),
    (OLD + "/", [NEW, OLD]),
    (NEW, [NEW, OLD]),
    # a server of one's own (testing): only that one
    ("http://192.168.1.10:8799/", ["http://192.168.1.10:8799"]),
])
def test_licence_server_order(option, expected):
    assert lic.licence_servers(option, NEW, OLD) == expected
