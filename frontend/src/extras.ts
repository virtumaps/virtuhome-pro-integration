// VirtuHome Pro's part of VirtuHome's Edit → Extras: the licence key, trials and the extensions there
// are. Drawn into the editor, so VirtuHome's editor classes (ed-card, ed-row, ed-btn, ed-in, ed-hint,
// ed-item) style it. Buying shows up only once VirtuMaps opens the shop on the licence server.
import { daysLeft, h } from "./dom";
import { t, useLanguage } from "./i18n";
import type { Catalog, Hass, Summary } from "./types";

export function drawExtras(box: HTMLElement, hass: Hass): void {
  useLanguage(hass);
  box.replaceChildren(h("p", { class: "ed-hint" }, "…"));
  const trial = (s: Summary) => s.kind === "trial";
  // paid and installer licences keep what is installed past their renewal date (lapsed) or once ended
  const statusText = (s: Summary) => ({
    active: trial(s) ? t("editor.extensions.trial") : t("editor.extensions.active"),
    lapsed: t("editor.extensions.lapsed"),
    ended: t("editor.extensions.ended"),
    expired: trial(s) ? t("editor.extensions.trialEnded") : t("editor.extensions.expiredRenewsOnline"),
  } as Record<string, string>)[s.status] ?? t("editor.extensions.notValid");
  const message = (err: unknown) => String((err as { message?: string }).message ?? err);
  const busy = (b: HTMLButtonElement, text: string) => {
    b.disabled = true;
    b.textContent = text;
  };

  const render = (s: Summary | null, catalog: Catalog, note = "", reload = false) => {
    const installed = new Set(s?.extensions.map((x) => x.id));
    const trials = new Map((s?.trials ?? []).map((x) => [x.id, x]));
    /** What an extension in the list says beside its name: installed, on trial or its trial over. */
    const tag = (id: string) => {
      const tr = trials.get(id);
      if (installed.has(id)) return t("editor.extensions.installed");
      if (tr?.status === "active" && tr.end !== null) return t("editor.extensions.trialDaysLeft", { n: daysLeft(tr.end) });
      if (tr) return t("editor.extensions.trialOver");
      return null;
    };
    const tryIt = (c: Catalog[number]) => h("button", { class: "ed-btn small", onclick: async (ev: Event) => {
      busy(ev.target as HTMLButtonElement, t("editor.extensions.starting"));
      try {
        render(await hass.callWS<Summary>({ type: "virtuhome_pro/licence/trial", ext: c.id }), catalog, t("editor.extensions.trialStartedReload"), true);
      } catch (err) {
        render(s, catalog, message(err));
      }
    } }, t("editor.extensions.tryItFree", { n: c.trial_days ?? 0 }));
    const input = h("input", { class: "ed-in", placeholder: t("editor.extensions.licenceKey"), autocomplete: "off", spellcheck: false });
    const actions = h("div", { class: "ed-row" });
    /** Remove licence asks first, in place of the buttons. */
    const askRemove = () => actions.replaceChildren(
      h("p", { class: "ed-hint" }, t("editor.extensions.removeTheLicenceFrom")),
      h("button", { class: "ed-btn small", onclick: async (ev: Event) => {
        busy(ev.target as HTMLButtonElement, "…");
        try {
          render(await hass.callWS<Summary>({ type: "virtuhome_pro/licence/remove" }), catalog, t("editor.extensions.licenceRemoved"));
        } catch (err) {
          render(s, catalog, message(err));
        }
      } }, t("editor.remove")),
      h("button", { class: "ed-btn ghost small", onclick: () => render(s, catalog, note, reload) }, t("editor.cancel")),
    );
    if (s && s.status !== "none") {
      actions.append(
        h("button", { class: "ed-btn ghost small", onclick: async (ev: Event) => {
          busy(ev.target as HTMLButtonElement, t("editor.extensions.checking"));
          try {
            render(await hass.callWS<Summary>({ type: "virtuhome_pro/licence/refresh" }), catalog, t("editor.extensions.upToDateReload"), true);
          } catch (err) {
            render(s, catalog, message(err));
          }
        } }, t("editor.extensions.checkForUpdates")),
        h("button", { class: "ed-btn ghost small", onclick: askRemove }, t("editor.extensions.removeLicence")),
      );
    }
    const parts: (Node | null)[] = [
      h("h4", {}, t("editor.extensions.licence")),
      s && s.status !== "none"
        ? h("div", { class: "ed-card" },
          h("div", { class: "ed-row" }, h("b", {}, statusText(s)), h("small", {}, s.key_hint ?? "")),
          s.error ? h("p", { class: "ed-hint" }, s.error) : null,
          ...s.extensions.map((x) => h("div", { class: "ed-item" }, h("span", {}, x.name), h("small", {}, x.version))),
          actions,
        )
        : h("p", { class: "ed-hint" }, t("editor.extensions.extensionsAddFeaturesSuch")),
      h("div", { class: "ed-row" },
        input,
        h("button", { class: "ed-btn small", onclick: async (ev: Event) => {
          const key = input.value.trim();
          if (key.length < 8) return;
          busy(ev.target as HTMLButtonElement, t("editor.extensions.activating"));
          try {
            const next = await hass.callWS<Summary>({ type: "virtuhome_pro/licence/activate", key });
            render(next, catalog, t("editor.extensions.activatedReloadThePage"), true);
          } catch (err) {
            render(s, catalog, message(err));
          }
        } }, t("editor.extensions.activate")),
      ),
      h("p", { class: "ed-hint" }, note),
      reload ? h("button", { class: "ed-btn ghost small", onclick: () => location.reload() }, t("editor.extensions.reloadNow")) : null,
      h("h4", {}, t("editor.extensions.availableExtensions")),
      ...(catalog.length ? catalog.map((c) => {
        const label = tag(c.id);
        const tried = trials.has(c.id);
        return h("div", { class: "ed-card" },
          h("div", { class: "ed-row" }, h("b", {}, c.name), label ? h("small", {}, label) : null),
          c.description ? h("p", { class: "ed-hint" }, c.description) : null,
          !installed.has(c.id) && tried && trials.get(c.id)!.status !== "active" ? h("p", { class: "ed-hint" }, t("editor.extensions.trialOverHint")) : null,
          !installed.has(c.id) && (c.checkout_url || (!tried && c.trial_days))
            ? h("div", { class: "ed-row" },
              !tried && c.trial_days ? tryIt(c) : null,
              c.checkout_url ? h("a", { class: `ed-btn small${!tried && c.trial_days ? " ghost" : ""}`, href: c.checkout_url, target: "_blank", rel: "noopener" }, t("editor.extensions.getItX", { x: c.price ? ` · ${c.price}` : "" })) : null)
            : null,
        );
      }) : [h("p", { class: "ed-hint" }, t("editor.extensions.theListOfExtensions"))]),
      !catalog.some((c) => c.checkout_url) ? h("p", { class: "ed-hint" }, t("editor.extensions.extensionsAreCurrentlyAvailable")) : null,
    ];
    box.replaceChildren(...parts.filter((x): x is Node => x !== null));
  };
  Promise.all([
    hass.callWS<Summary>({ type: "virtuhome_pro/licence/get" }).catch(() => null),
    hass.callWS<Catalog>({ type: "virtuhome_pro/catalog" }).catch(() => [] as Catalog),
  ]).then(([s, c]) => render(s, c, s ? "" : t("editor.extensions.extensionsNeedTheVirtuhome")));
}
