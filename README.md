# VirtuHome Pro

Extensions for [VirtuHome](https://github.com/virtumaps/virtuhome), the live 3D home for Home
Assistant: **Energy**, **Security**, **Household**, **Wall Tablet** and **Network**. This
integration takes your licence key (or starts a free trial), downloads the extensions it unlocks,
checks their signatures, keeps them working offline, and hands them to VirtuHome.

VirtuMaps' extensions are currently available to VirtuMaps installation clients.

## Install

You need VirtuHome 0.18 or later (from HACS) and HACS.

[![Open VirtuHome Pro in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=virtumaps&repository=virtuhome-pro-integration&category=integration)

1. Tap the button above, or in VirtuHome open Edit → **Extras** → **Open in HACS**. HACS asks to
   add this repository: **Add**. (By hand: HACS → ⋮ → **Custom repositories**, add
   `virtumaps/virtuhome-pro-integration` with the type **Integration**.)
2. **Download**, then restart Home Assistant.
3. VirtuHome Pro sets itself up after the restart. Reload the page, then enter your licence key in
   VirtuHome → Edit → **Extras** → **Activate**, and **Reload now**.

Updates come through HACS. Coming from VirtuHome 0.17 or earlier, where extensions were part of
VirtuHome: your key, trials, extensions and the automations they added carry on as they were.

The [VirtuHome guide](https://virtumaps.github.io/virtuhome/#extensions-and-virtuhome-pro) says
what each extension does and how keys, trials and updates work.

## What is sent

Nothing until you enter a key or start a trial. Then VirtuHome Pro asks the VirtuMaps licence server
(`license.virtumaps.com`) for the list of extensions and your extensions' updates, about once a day,
sending the key and an anonymous code for this Home Assistant: nothing that names your home.
Starting a trial sends the extension's name and the same code. The extensions are stored in Home
Assistant and keep working offline; a bought extension keeps working at the version you have, for
good.

## What is in this repository

This integration (GPL-3.0): the licence key and trials, downloading and checking the extensions,
serving them, the automations they add from their signed blueprints, and its part of VirtuHome's
Extras tab. The extensions themselves are commercial software by VirtuMaps, not part of this
repository and not under its licence; they are downloaded, for a licence, from the licence server.
How it works and what an extension may do in Home Assistant: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Support

Installation clients: the contact you were given, or info@virtumaps.com. Problems with this
integration: [issues](https://github.com/virtumaps/virtuhome-pro-integration/issues), with
Settings → Devices & services → VirtuHome Pro → ⋮ → **Download diagnostics** attached (it has no
licence key or token).

## Development

```bash
cd frontend && npm ci && npm run typecheck && npm test && npm run build   # commit the build
pip install cryptography pytest voluptuous && pytest -q tests
```
