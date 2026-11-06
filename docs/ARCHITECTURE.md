# How VirtuHome Pro works

## Pieces

| Path | What |
|---|---|
| `custom_components/virtuhome_pro/` | The integration: the licence and trials (`extensions.py`, `licensing.py`, stored in `.storage/virtuhome.licence`, where VirtuHome up to 0.17 kept it), the extensions' automations (`automations.py`, `automation_store.py`), WebSocket API (`virtuhome_pro/extensions` for every user, `virtuhome_pro/licence/*`, `virtuhome_pro/catalog` and `virtuhome_pro/automations/*` for admins), Repairs and diagnostics. Needs VirtuHome 0.18 or later and won't start beside an older one. |
| `frontend/src/index.ts` | The module Home Assistant loads on every page (`add_extra_js_url`), a few hundred bytes. It registers VirtuHome Pro as an extension source with VirtuHome (`(window.virtuhomeSources ||= []).push(source)`): its extensions, each imported from `/virtuhome_ext/`; its part of Edit → Extras (`extras.ts`); its Check my setup lines (`check.ts`); and the WebSocket prefix for its extensions' automations. The last three are chunks fetched only when VirtuHome's editor asks. |
| `frontend/src/i18n.ts` | Its texts in English, German and Dutch (the keys VirtuHome had for them). |

VirtuHome itself has no licence code and loads no code from outside its repository; it hands each
extension a source brings its API (VirtuHome's `frontend/src/ext/api.ts`, `EXT_API_VERSION`).

**Setting itself up.** VirtuHome Pro asks for nothing. Once HACS has put it in and Home Assistant
restarted, VirtuHome starts its integration discovery flow, and `config_flow.py` creates the entry
there and then (taking a licence server set in VirtuHome's options before 0.18).

## Extensions and what they may do in Home Assistant

Extensions are ES modules signed by the licence server's Ed25519 key; the integration holds only
the public key (`licensing.py`). It downloads them for a licence (`extensions.py`), checks each file
against the checksum and signature from the server, keeps both beside it in
`.virtuhome/extensions/`, and serves them at `/virtuhome_ext/`. Paid and installer licences keep
loading what is installed after their renewal date; a trial stops at its end.

**No extension code runs inside Home Assistant.** For what has to happen with no screen open (an
alert when the garage is left open), an extension ships automation blueprints: plain YAML in its
bundle's last line, `//# virtuhome-blueprints=<base64 of JSON {"<id>": "<yaml>"}>`, so the bundle's
signature covers them. The integration (`automations.py`, `automation_store.py`):

- Uses only blueprints it reads itself from an installed extension's bundle on disk, after checking
  the file against the signature stored with it. The browser names a blueprint and gives its
  inputs; it never sends YAML. Unknown blueprints, changed bundles and bundles stored without a
  signature (by an older VirtuHome, until the next renewal) are refused.
- Checks the inputs against the blueprint's inputs and their selectors: entity, device and area ids
  that exist (entities of the domains the selector allows), numbers in range, times, durations,
  choices and short text without templates. Other selectors (actions, objects, templates) are
  refused, so what an automation does is what the signed blueprint says.
- Adds an automation only when the user agreed in VirtuHome's own dialog, which shows its name, its
  triggers, conditions and actions with the inputs filled in, and where its notifications go
  (Home Assistant's notify services). The WebSocket commands (`virtuhome_pro/automations/*`) are
  for admins only. Extensions run in
  the same page as the core, so the dialog is a rule the core's API keeps, not a wall against
  extension code: the limit on what an extension can make Home Assistant do is the signed blueprints.
- Writes through Home Assistant's own code, as its editors do (the same calls from 2025.1 to now):
  the blueprint to `blueprints/automation/virtuhome/<extension>/<id>.yaml` through the automation
  blueprints' `DomainBlueprints`, the automation checked with the automation editor's validator,
  added to `automations.yaml` with Home Assistant's YAML loader and dumper, and reloaded on its own.
  If Home Assistant doesn't load `automations.yaml`, the automation is taken out again.
- Tags each automation by its id, `virtuhome-<extension>-<hex>`, and finds them in
  `automations.yaml` by it. They show in Settings → Automations and can be changed there.
- Removes an extension's automations, and its blueprints unless another automation uses one, when
  the extension goes: its licence removed or revoked, the extension no longer in it, or a trial
  ended (checked at start and daily).
