// VirtuHome Pro's frontend module. Home Assistant loads it on every page (add_extra_js_url), so it
// stays tiny: it registers the extension source with VirtuHome, and the Extras section and Check my
// setup lines are chunks of their own, fetched when VirtuHome's editor asks for them.
//
// VirtuHome takes sources pushed onto window.virtuhomeSources before or after it loads, and hands
// each extension its API; the extensions' modules are imported here, from this integration.
import type { ExtensionSource, Hass, SourceExtension, Summary } from "./types";

type Listed = { id: string; name: string; version: string; url: string }[];

const source: ExtensionSource = {
  id: "virtuhome_pro",
  name: "VirtuHome Pro",
  automations: "virtuhome_pro/automations",
  async extensions(hass: Hass): Promise<SourceExtension[]> {
    const list = await hass.callWS<Listed>({ type: "virtuhome_pro/extensions" });
    return list.map((e) => ({ id: e.id, name: e.name, version: e.version, load: () => import(/* @vite-ignore */ e.url) }));
  },
  extras(el: HTMLElement, hass: Hass): void {
    void import("./extras").then((m) => m.drawExtras(el, hass));
  },
  async check(hass: Hass) {
    const [{ licenceCheck }, { useLanguage }] = await Promise.all([import("./check"), import("./i18n")]);
    useLanguage(hass);
    return licenceCheck(await hass.callWS<Summary>({ type: "virtuhome_pro/licence/get" }).catch(() => null));
  },
  async renew(hass: Hass): Promise<void> {
    await hass.callWS({ type: "virtuhome_pro/licence/refresh" });
  },
};

type Queue = { push(s: ExtensionSource): unknown };
const w = window as unknown as { virtuhomeSources?: Queue };
(w.virtuhomeSources ??= [] as unknown as Queue).push(source);
