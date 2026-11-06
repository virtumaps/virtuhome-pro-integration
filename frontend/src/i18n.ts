// Text shown to users, in the user's language: VirtuHome's own texts for the licence and extensions,
// which moved here with them (keys as VirtuHome had them). A key a language lacks shows in English.
//
// Placeholders are named, {name}. A text with forms for counts is { one, other }, picked by {n}.

type Plural = { one?: string; other: string };
type Text = string | Plural;
type Table = Readonly<Record<string, Text>>;

const EN = {
  "checks.extensions.active": "Licence active.",
  "checks.extensions.activeWith": "Licence active: {names}.",
  "checks.extensions.ended": "Licence ended: the installed extensions keep working, without new versions.",
  "checks.extensions.expired": "The licence has expired. Its extensions stop until it renews.",
  "checks.extensions.expiredWhy": "The licence has expired ({error}). Its extensions stop until it renews.",
  "checks.extensions.invalid": "The licence key isn't valid here.",
  "checks.extensions.invalidWhy": "The licence key isn't valid here ({error}).",
  "checks.extensions.lapsed": "The licence is past its renewal date, so new versions wait until it renews online. The installed extensions keep working.",
  "checks.extensions.none": "No licence key, so no extensions.",
  "checks.extensions.renewFailed": "The licence couldn't be renewed lately ({error}). Extensions keep working meanwhile.",
  "checks.extensions.trialEnded": "The trial has ended, so its extensions have stopped.",
  "checks.extensions.trialOver": "The trial of {names} has ended, so it no longer loads. Nothing else in the home changed; Extras says how to get it.",
  "checks.extensions.trying": "Trying {list}.",
  "checks.extensions.tryingOne": { one: "{name} ({n} day left)", other: "{name} ({n} days left)" },
  "editor.cancel": "Cancel",
  "editor.extensions.activate": "Activate",
  "editor.extensions.activatedReloadThePage": "Activated. Reload the page to start using the extensions.",
  "editor.extensions.activating": "Activating…",
  "editor.extensions.active": "Active",
  "editor.extensions.availableExtensions": "Available extensions",
  "editor.extensions.checkForUpdates": "Check for updates",
  "editor.extensions.checking": "Checking…",
  "editor.extensions.ended": "Yours to keep — no new versions",
  "editor.extensions.expiredRenewsOnline": "Expired — renews online",
  "editor.extensions.extensionsAddFeaturesSuch": "Extensions add features such as the wall tablet mode. Enter the licence key you got from VirtuMaps.",
  "editor.extensions.extensionsAreCurrentlyAvailable": "Extensions are currently available to VirtuMaps installation clients.",
  "editor.extensions.extensionsNeedTheVirtuhome": "VirtuHome Pro isn't set up yet: restart Home Assistant, then reload the page.",
  "editor.extensions.getItX": "Get it{x}",
  "editor.extensions.installed": "· installed",
  "editor.extensions.lapsed": "Yours to keep — new versions once it renews online",
  "editor.extensions.licence": "Licence",
  "editor.extensions.licenceKey": "Licence key",
  "editor.extensions.licenceRemoved": "Licence removed.",
  "editor.extensions.notValid": "Not valid",
  "editor.extensions.reloadNow": "Reload now",
  "editor.extensions.removeLicence": "Remove licence",
  "editor.extensions.removeTheLicenceFrom": "Remove the licence from this Home Assistant? Its extensions stop working here, the automations they added are removed, and the activation is freed for another one.",
  "editor.extensions.starting": "Starting…",
  "editor.extensions.theListOfExtensions": "The list of extensions could not be loaded right now.",
  "editor.extensions.trial": "Trial",
  "editor.extensions.trialDaysLeft": { one: "· trial, {n} day left", other: "· trial, {n} days left" },
  "editor.extensions.trialEnded": "Trial ended",
  "editor.extensions.trialOver": "· trial ended",
  "editor.extensions.trialOverHint": "The trial has ended, so it no longer loads here. Nothing else in your home changed.",
  "editor.extensions.trialStartedReload": "Your trial has started. Reload the page to start using it.",
  "editor.extensions.tryItFree": { one: "Try it free for {n} day", other: "Try it free for {n} days" },
  "editor.extensions.upToDateReload": "Up to date. Reload the page to use new versions.",
  "editor.remove": "Remove",
} as const;

const DE: Table = {
  "checks.extensions.active": "Lizenz aktiv.",
  "checks.extensions.activeWith": "Lizenz aktiv: {names}.",
  "checks.extensions.ended": "Lizenz beendet: die installierten Erweiterungen funktionieren weiter, ohne neue Versionen.",
  "checks.extensions.expired": "Die Lizenz ist abgelaufen. Ihre Erweiterungen stoppen, bis sie sich erneuert.",
  "checks.extensions.expiredWhy": "Die Lizenz ist abgelaufen ({error}). Ihre Erweiterungen stoppen, bis sie sich erneuert.",
  "checks.extensions.invalid": "Der Lizenzschlüssel ist hier nicht gültig.",
  "checks.extensions.invalidWhy": "Der Lizenzschlüssel ist hier nicht gültig ({error}).",
  "checks.extensions.lapsed": "Die Lizenz ist über ihr Erneuerungsdatum hinaus, neue Versionen warten also, bis sie sich online erneuert. Die installierten Erweiterungen funktionieren weiter.",
  "checks.extensions.none": "Kein Lizenzschlüssel, daher keine Erweiterungen.",
  "checks.extensions.renewFailed": "Die Lizenz konnte zuletzt nicht erneuert werden ({error}). Die Erweiterungen funktionieren solange weiter.",
  "checks.extensions.trialEnded": "Die Testphase ist vorbei, daher sind ihre Erweiterungen gestoppt.",
  "checks.extensions.trialOver": "Die Testphase von {names} ist vorbei, daher wird es nicht mehr geladen. Sonst hat sich im Zuhause nichts geändert; unter Extras steht, wie du es bekommst.",
  "checks.extensions.trying": "Im Test: {list}.",
  "checks.extensions.tryingOne": { one: "{name} (noch {n} Tag)", other: "{name} (noch {n} Tage)" },
  "editor.cancel": "Abbrechen",
  "editor.extensions.activate": "Aktivieren",
  "editor.extensions.activatedReloadThePage": "Aktiviert. Lade die Seite neu, um die Erweiterungen zu nutzen.",
  "editor.extensions.activating": "Wird aktiviert…",
  "editor.extensions.active": "Aktiv",
  "editor.extensions.availableExtensions": "Verfügbare Erweiterungen",
  "editor.extensions.checkForUpdates": "Nach Updates suchen",
  "editor.extensions.checking": "Wird geprüft…",
  "editor.extensions.ended": "Gehört dir — keine neuen Versionen",
  "editor.extensions.expiredRenewsOnline": "Abgelaufen — erneuert sich online",
  "editor.extensions.extensionsAddFeaturesSuch": "Erweiterungen bringen Funktionen wie den Wandtablet-Modus. Gib den Lizenzschlüssel ein, den du von VirtuMaps bekommen hast.",
  "editor.extensions.extensionsAreCurrentlyAvailable": "Erweiterungen gibt es derzeit für Installationskunden von VirtuMaps.",
  "editor.extensions.extensionsNeedTheVirtuhome": "VirtuHome Pro ist noch nicht eingerichtet: Starte Home Assistant neu und lade dann die Seite neu.",
  "editor.extensions.getItX": "Holen{x}",
  "editor.extensions.installed": "· installiert",
  "editor.extensions.lapsed": "Gehört dir — neue Versionen, sobald sie sich online erneuert",
  "editor.extensions.licence": "Lizenz",
  "editor.extensions.licenceKey": "Lizenzschlüssel",
  "editor.extensions.licenceRemoved": "Lizenz entfernt.",
  "editor.extensions.notValid": "Nicht gültig",
  "editor.extensions.reloadNow": "Jetzt neu laden",
  "editor.extensions.removeLicence": "Lizenz entfernen",
  "editor.extensions.removeTheLicenceFrom": "Die Lizenz von diesem Home Assistant entfernen? Ihre Erweiterungen funktionieren hier nicht mehr, die Automatisierungen, die sie hinzugefügt haben, werden entfernt, und die Aktivierung wird für ein anderes frei.",
  "editor.extensions.starting": "Wird gestartet…",
  "editor.extensions.theListOfExtensions": "Die Liste der Erweiterungen konnte gerade nicht geladen werden.",
  "editor.extensions.trial": "Test",
  "editor.extensions.trialDaysLeft": { one: "· Test, noch {n} Tag", other: "· Test, noch {n} Tage" },
  "editor.extensions.trialEnded": "Test beendet",
  "editor.extensions.trialOver": "· Test beendet",
  "editor.extensions.trialOverHint": "Die Testphase ist vorbei, daher wird es hier nicht mehr geladen. Sonst hat sich in deinem Zuhause nichts geändert.",
  "editor.extensions.trialStartedReload": "Dein Test hat begonnen. Lade die Seite neu, um es zu nutzen.",
  "editor.extensions.tryItFree": { one: "{n} Tag kostenlos testen", other: "{n} Tage kostenlos testen" },
  "editor.extensions.upToDateReload": "Aktuell. Lade die Seite neu, um neue Versionen zu nutzen.",
  "editor.remove": "Entfernen",
};

const NL: Table = {
  "checks.extensions.active": "Licentie actief.",
  "checks.extensions.activeWith": "Licentie actief: {names}.",
  "checks.extensions.ended": "Licentie beëindigd: de geïnstalleerde uitbreidingen blijven werken, zonder nieuwe versies.",
  "checks.extensions.expired": "De licentie is verlopen. De uitbreidingen stoppen tot hij vernieuwd is.",
  "checks.extensions.expiredWhy": "De licentie is verlopen ({error}). De uitbreidingen stoppen tot hij vernieuwd is.",
  "checks.extensions.invalid": "De licentiesleutel is hier niet geldig.",
  "checks.extensions.invalidWhy": "De licentiesleutel is hier niet geldig ({error}).",
  "checks.extensions.lapsed": "De licentie is over zijn vernieuwingsdatum, dus nieuwe versies wachten tot hij online vernieuwd is. De geïnstalleerde uitbreidingen blijven werken.",
  "checks.extensions.none": "Geen licentiesleutel, dus geen uitbreidingen.",
  "checks.extensions.renewFailed": "De licentie kon onlangs niet worden vernieuwd ({error}). De uitbreidingen blijven intussen werken.",
  "checks.extensions.trialEnded": "De proefperiode is voorbij, dus de uitbreidingen zijn gestopt.",
  "checks.extensions.trialOver": "De proefperiode van {names} is voorbij, dus het wordt niet meer geladen. Verder is er niets in huis veranderd; onder Extra's staat hoe je het krijgt.",
  "checks.extensions.trying": "Op proef: {list}.",
  "checks.extensions.tryingOne": { one: "{name} (nog {n} dag)", other: "{name} (nog {n} dagen)" },
  "editor.cancel": "Annuleren",
  "editor.extensions.activate": "Activeren",
  "editor.extensions.activatedReloadThePage": "Geactiveerd. Laad de pagina opnieuw om de uitbreidingen te gebruiken.",
  "editor.extensions.activating": "Activeren…",
  "editor.extensions.active": "Actief",
  "editor.extensions.availableExtensions": "Beschikbare uitbreidingen",
  "editor.extensions.checkForUpdates": "Zoeken naar updates",
  "editor.extensions.checking": "Controleren…",
  "editor.extensions.ended": "Van jou — geen nieuwe versies",
  "editor.extensions.expiredRenewsOnline": "Verlopen — vernieuwt online",
  "editor.extensions.extensionsAddFeaturesSuch": "Uitbreidingen voegen functies toe zoals de wandtabletmodus. Vul de licentiesleutel in die je van VirtuMaps kreeg.",
  "editor.extensions.extensionsAreCurrentlyAvailable": "Uitbreidingen zijn er nu voor installatieklanten van VirtuMaps.",
  "editor.extensions.extensionsNeedTheVirtuhome": "VirtuHome Pro is nog niet ingesteld: start Home Assistant opnieuw en laad dan de pagina opnieuw.",
  "editor.extensions.getItX": "Nemen{x}",
  "editor.extensions.installed": "· geïnstalleerd",
  "editor.extensions.lapsed": "Van jou — nieuwe versies zodra hij online vernieuwd is",
  "editor.extensions.licence": "Licentie",
  "editor.extensions.licenceKey": "Licentiesleutel",
  "editor.extensions.licenceRemoved": "Licentie verwijderd.",
  "editor.extensions.notValid": "Niet geldig",
  "editor.extensions.reloadNow": "Nu opnieuw laden",
  "editor.extensions.removeLicence": "Licentie verwijderen",
  "editor.extensions.removeTheLicenceFrom": "De licentie van deze Home Assistant verwijderen? De uitbreidingen werken hier niet meer, de automatiseringen die ze toevoegden worden verwijderd, en de activering komt vrij voor een andere.",
  "editor.extensions.starting": "Starten…",
  "editor.extensions.theListOfExtensions": "De lijst met uitbreidingen kon nu niet worden geladen.",
  "editor.extensions.trial": "Proef",
  "editor.extensions.trialDaysLeft": { one: "· proef, nog {n} dag", other: "· proef, nog {n} dagen" },
  "editor.extensions.trialEnded": "Proef voorbij",
  "editor.extensions.trialOver": "· proef voorbij",
  "editor.extensions.trialOverHint": "De proefperiode is voorbij, dus het wordt hier niet meer geladen. Verder is er niets in je huis veranderd.",
  "editor.extensions.trialStartedReload": "Je proefperiode is begonnen. Laad de pagina opnieuw om het te gebruiken.",
  "editor.extensions.tryItFree": { one: "{n} dag gratis proberen", other: "{n} dagen gratis proberen" },
  "editor.extensions.upToDateReload": "Bijgewerkt. Laad de pagina opnieuw om nieuwe versies te gebruiken.",
  "editor.remove": "Verwijderen",
};

export type Key = keyof typeof EN;
const TABLES: Record<string, Table> = { en: EN, de: DE, nl: NL };

/** The table for Home Assistant's language, else its main language, else English. */
export function language(hass: { language?: string; locale?: { language?: string } } | null): string {
  const lang = (hass?.locale?.language || hass?.language || "en").toLowerCase();
  if (TABLES[lang]) return lang;
  const main = lang.split("-")[0];
  return TABLES[main] ? main : "en";
}

let current = "en";
export const useLanguage = (hass: Parameters<typeof language>[0]): void => {
  current = language(hass);
};

export function t(key: Key, params: Record<string, string | number> = {}): string {
  let text: Text = TABLES[current]?.[key] ?? EN[key];
  if (typeof text !== "string") {
    const n = Number(params.n ?? 0);
    const form = new Intl.PluralRules(current).select(n) as keyof Plural;
    text = text[form] ?? text.other;
  }
  return text.replace(/\{(\w+)\}/g, (m, name: string) => (name in params ? String(params[name]) : m));
}
