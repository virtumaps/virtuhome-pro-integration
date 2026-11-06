"""Paid extensions: activate a licence key, download the extensions it unlocks, keep them updated.

Nothing here talks to the internet unless a licence key was entered or a trial started. Once
activated, extensions are stored locally and keep working offline; a daily check fetches updates and
renews the licence. Paid and installer licences keep loading what is installed after their renewal
date (licensing.py); a trial stops at its end, and a licence the server says was revoked stops at the
next renewal. Automations an extension added from its blueprints (automation_store.py) go when it goes.

Trials sit beside the licence, one signed token per extension (no key), and end on their own date.
The licence server is reached at our own address, else the first one (const.py), unless the options
name another.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import instance_id
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store

from .automation_store import AutomationStore
from .const import DEFAULT_LICENCE_SERVER, EXT_URL_BASE, LICENCE_KEY_STORE, OLD_LICENCE_SERVER, STORAGE_VERSION
from .licensing import (
    Licence, LicenceError, ends_licence, installation_hash, licence_servers, licence_state, loadable, read_token,
    to_keep, verify_bundle, verify_token, with_trials,
)

_LOGGER = logging.getLogger(__name__)
TIMEOUT = aiohttp.ClientTimeout(total=30)


class ExtensionManager:
    def __init__(self, hass: HomeAssistant, server: str | None) -> None:
        self.hass = hass
        self.servers = licence_servers(server, DEFAULT_LICENCE_SERVER, OLD_LICENCE_SERVER)
        # the address that last answered
        self.server = self.servers[0]
        self.folder = Path(hass.config.path(".virtuhome", "extensions"))
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, LICENCE_KEY_STORE)
        self.data: dict[str, Any] = {}
        self.instance = ""
        self.status = "none"  # none | active | lapsed | ended | expired | invalid
        self.licence: Licence | None = None
        self.error: str | None = None
        # the bundles on disk: read at load and after each prune, so extensions() never touches the disk
        self._present: set[str] = set()
        self._unsub_timer = None
        self._unsub_started = None
        self.automations = AutomationStore(hass, self)

    async def async_load(self) -> None:
        self.instance = installation_hash(await instance_id.async_get(self.hass))
        self.data = await self._store.async_load() or {}
        self._present = await self.hass.async_add_executor_job(self._on_disk)
        self._check()
        self._watch()
        # automations of extensions that went while Home Assistant was off (a trial that ended)
        self._unsub_started = async_at_started(self.hass, self._tidy)

    @callback
    def async_unload(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
        if self._unsub_started:
            self._unsub_started()
            self._unsub_started = None

    def _watch(self) -> None:
        """The daily check runs while there is a licence or a trial."""
        if not self._unsub_timer and (self.data.get("key") or self.data.get("trials")):
            self._unsub_timer = async_track_time_interval(self.hass, self._daily, timedelta(hours=24))

    def _trials(self) -> list[tuple[str, Licence | None, list[dict[str, Any]]]]:
        """Each trial: its extension, what its token allows now (None when it doesn't check out) and its files."""
        out = []
        for ext_id, trial in (self.data.get("trials") or {}).items():
            try:
                licence: Licence | None = licence_state(read_token(trial.get("token", ""), self.instance))
            except LicenceError:
                licence = None
            out.append((ext_id, licence, trial.get("extensions", [])))
        return out

    def _check(self) -> Licence | None:
        token = self.data.get("token")
        self.licence = None
        if not token:
            self.status = "none"
            return None
        try:
            self.licence = licence_state(read_token(token, self.instance))
        except LicenceError as err:
            self.status = "invalid"
            self.error = str(err)
            return None
        self.status = self.licence.status
        return self.licence

    # ------------------------------------------------------------------ what the frontend loads

    def extensions(self) -> list[dict[str, str]]:
        """Extensions to load now: unlocked by the licence (also past its renewal date unless it was a
        trial) and present on disk. Runs on every card and panel load, so from memory only."""
        return [
            {"id": ext["id"], "name": ext["name"], "version": ext["version"], "url": f"{EXT_URL_BASE}/{ext['file']}"}
            for ext in self.installed()
            if ext["file"] in self._present
        ]

    def installed(self) -> list[dict[str, Any]]:
        """The installed extensions that load now, as stored (file, checksum and signature): the
        licence's, then those on a trial that hasn't ended."""
        main = loadable(self.data.get("extensions", []), self._check())
        return with_trials(main, [(licence, entries) for _id, licence, entries in self._trials()])

    def _keep(self) -> set[str]:
        """Extensions whose automations stay: the installed ones, none once a trial has ended."""
        keep: set[str] = set()
        if self.licence is None or self.licence.loads:
            keep = {e["id"] for e in self.data.get("extensions", [])}
        return keep | {e["id"] for e in with_trials([], [(lic, entries) for _id, lic, entries in self._trials()])}

    def _files(self) -> set[str]:
        """The bundles to keep on disk: the licence's and those of trials that haven't ended."""
        files = {e["file"] for e in self.data.get("extensions", [])}
        for _id, licence, entries in self._trials():
            if licence is not None and licence.loads:
                files |= {e["file"] for e in entries}
        return files

    async def _tidy(self, _hass: Any = None) -> None:
        self._check()
        try:
            await self.automations.async_sweep(self._keep())
        except Exception:  # noqa: BLE001 - tidying never stops a licence from working
            _LOGGER.exception("Could not tidy up the automations of removed extensions")

    def summary(self) -> dict[str, Any]:
        key = self.data.get("key") or ""
        return {
            "status": self.status,
            "kind": self.licence.kind if self.licence else None,
            "error": self.error,
            "key_hint": f"{key[:4]}…{key[-4:]}" if len(key) > 8 else None,
            "extensions": [{k: e[k] for k in ("id", "name", "version")} for e in self.data.get("extensions", [])],
            "checked": self.data.get("checked"),
            "server": self.server,
            "trials": [
                {
                    "id": ext_id,
                    "name": entries[0].get("name", ext_id) if entries else ext_id,
                    "version": entries[0].get("version") if entries else None,
                    "end": licence.exp if licence else None,
                    "status": licence.status if licence else "invalid",
                }
                for ext_id, licence, entries in self._trials()
            ],
        }

    # ------------------------------------------------------------------ licence server

    async def _fetch(self, method: str, path: str, **kwargs: Any) -> tuple[int, bytes]:
        """Asks the licence server, at the address that answered last first, then the others while
        one can't be reached or fails on its side (5xx); returns the status and the body."""
        session = async_get_clientsession(self.hass)
        order = [self.server, *[s for s in self.servers if s != self.server]]
        failed: Exception | None = None
        for i, server in enumerate(order):
            try:
                async with session.request(method, f"{server}{path}", timeout=TIMEOUT, **kwargs) as resp:
                    body = await resp.read()
                    if resp.status >= 500 and i < len(order) - 1:
                        failed = aiohttp.ClientResponseError(resp.request_info, resp.history, status=resp.status)
                        continue
                    self.server = server
                    return resp.status, body
            except (aiohttp.ClientConnectionError, TimeoutError) as err:
                failed = err
        assert failed is not None
        raise failed

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        status, raw = await self._fetch("POST", path, json=body)
        try:
            data = json.loads(raw) if raw else {}
        except ValueError:
            data = {}
        if status >= 400:
            raise LicenceError(data.get("message") or data.get("error") or f"licence server answered {status}")
        return data

    async def async_catalog(self) -> list[dict[str, Any]]:
        """What can be bought or tried (names, prices, checkout links, trial days)."""
        status, raw = await self._fetch("GET", "/v1/catalog")
        if status >= 400:
            raise LicenceError(f"licence server answered {status}")
        return json.loads(raw).get("extensions", [])

    async def async_activate(self, key: str) -> dict[str, Any]:
        key = key.strip()
        # only the key and the anonymous installation id: nothing that names the home
        data = await self._post("/v1/activate", {"key": key, "instance": self.instance})
        await self._accept(key, data)
        if not self._unsub_timer:
            self._unsub_timer = async_track_time_interval(self.hass, self._daily, timedelta(hours=24))
        return self.summary()

    async def async_trial(self, ext_id: str) -> dict[str, Any]:
        """Starts a trial of one extension here (no key: the server allows one per extension and home)."""
        await self._renew_trial(ext_id)
        self._watch()
        return self.summary()

    async def _renew_trial(self, ext_id: str) -> None:
        # only the extension and the anonymous installation id
        data = await self._post("/v1/trial", {"ext": ext_id, "instance": self.instance})
        token = data["token"]
        licence = licence_state(verify_token(token, self.instance))
        if licence.kind != "trial" or ext_id not in licence.ext:
            raise LicenceError("the licence server sent something other than a trial")
        before = (self.data.get("trials") or {}).get(ext_id, {}).get("extensions", [])
        offered = [e for e in data.get("extensions", []) if e.get("id") == ext_id]
        installed = await self._install(to_keep(before, offered, licence), token, licence)
        trials = dict(self.data.get("trials") or {})
        trials[ext_id] = {"token": token, "activation": data.get("activation"), "extensions": installed}
        self.data = {**self.data, "trials": trials}
        self._present = await self.hass.async_add_executor_job(self._prune, self._files())
        await self._store.async_save(self.data)
        await self._tidy()

    async def _refresh_trials(self) -> None:
        """Trials still running get the newest version; one the server won't renew runs to its end."""
        for ext_id, licence, _entries in self._trials():
            if licence is None or licence.status != "active":
                continue
            try:
                await self._renew_trial(ext_id)
            except (aiohttp.ClientError, TimeoutError, LicenceError) as err:
                _LOGGER.debug("Trial of %s not renewed: %s", ext_id, err)

    async def async_refresh(self) -> dict[str, Any]:
        await self._refresh_trials()
        key = self.data.get("key")
        if not key:
            self._present = await self.hass.async_add_executor_job(self._prune, self._files())
            return self.summary()
        try:
            data = await self._post("/v1/refresh", {"key": key, "activation": self.data.get("activation"), "instance": self.instance})
        except (aiohttp.ClientError, TimeoutError) as err:
            # offline: keep what is installed, the token carries its own expiry
            self.error = f"could not reach the licence server: {err}"
            return self.summary()
        except LicenceError as err:
            if ends_licence(str(err)):
                await self._wipe()
            self.error = str(err)
            return self.summary()
        await self._accept(key, data)
        return self.summary()

    async def async_remove(self) -> dict[str, Any]:
        key = self.data.get("key")
        if key:
            try:
                await self._post("/v1/deactivate", {"key": key, "activation": self.data.get("activation"), "instance": self.instance})
            except (aiohttp.ClientError, TimeoutError, LicenceError) as err:
                _LOGGER.warning("Could not free the activation on the licence server: %s", err)
        await self._wipe()
        return self.summary()

    async def _accept(self, key: str, data: dict[str, Any]) -> None:
        """Checks the new token, downloads and verifies the unlocked extensions, then stores it all.

        A licence that gets no updates (marked ended) keeps the installed versions and downloads nothing."""
        token = data["token"]
        licence = licence_state(verify_token(token, self.instance))
        keep = to_keep(self.data.get("extensions", []), data.get("extensions", []), licence)
        installed = await self._install(keep, token, licence)
        self.data = {
            "key": key, "activation": data.get("activation"), "token": token, "extensions": installed, "checked": time.time(),
            **({"trials": self.data["trials"]} if self.data.get("trials") else {}),
        }
        self._present = await self.hass.async_add_executor_job(self._prune, self._files())
        self.error = None
        await self._store.async_save(self.data)
        await self._tidy()

    async def _install(self, keep: list[dict[str, Any]], token: str, licence: Licence) -> list[dict[str, Any]]:
        """Downloads (while the licence gets updates) and checks each bundle; returns them as stored."""
        await self.hass.async_add_executor_job(lambda: self.folder.mkdir(parents=True, exist_ok=True))
        installed = []
        for ext in keep:
            file = f"{ext['id']}-{ext['version']}.js"
            if licence.updates and not await self.hass.async_add_executor_job(self._verified, ext, file):
                status, body = await self._fetch(
                    "GET", f"/v1/extensions/{ext['id']}/{ext['version']}", headers={"Authorization": f"Bearer {token}"},
                )
                if status >= 400:
                    raise LicenceError(f"{ext['id']} {ext['version']}: licence server answered {status}")
                verify_bundle(ext["id"], ext["version"], body, ext["sha256"], ext["sig"])
                await self.hass.async_add_executor_job((self.folder / file).write_bytes, body)
            # the checksum and signature stay with it, so the stored bundle can be checked again later
            installed.append({
                "id": ext["id"], "name": ext.get("name", ext["id"]), "version": ext["version"], "file": file,
                **{k: ext[k] for k in ("sha256", "sig") if k in ext},
            })
        return installed

    def _verified(self, ext: dict[str, Any], file: str) -> bool:
        """The bundle is on disk and is the one the server signed."""
        path = self.folder / file
        if not path.is_file():
            return False
        try:
            verify_bundle(ext["id"], ext["version"], path.read_bytes(), ext["sha256"], ext["sig"])
        except LicenceError:
            return False
        return True

    def _prune(self, keep: set[str]) -> set[str]:
        """Deletes the bundles not in keep; returns those left."""
        for f in self.folder.glob("*.js"):
            if f.name not in keep:
                f.unlink(missing_ok=True)
        return self._on_disk()

    def _on_disk(self) -> set[str]:
        return {f.name for f in self.folder.glob("*.js")}

    async def _wipe(self) -> None:
        """The licence goes; trials stay until their end."""
        trials = self.data.get("trials")
        self.data = {"trials": trials} if trials else {}
        self._present = await self.hass.async_add_executor_job(self._prune, self._files())
        if trials:
            await self._store.async_save(self.data)
        else:
            await self._store.async_remove()
        await self._tidy()

    async def _daily(self, _now: Any = None) -> None:
        await self.async_refresh()
        # a trial that ended: its bundle and automations go
        self._present = await self.hass.async_add_executor_job(self._prune, self._files())
        await self._tidy()
