// What VirtuHome Pro says in VirtuHome's Check my setup: the licence and trials. VirtuHome adds the
// extensions that can't load.
import { daysLeft } from "./dom";
import { t } from "./i18n";
import type { SourceCheck, Summary } from "./types";

/** How long after its end a trial still gets a note. */
const TRIAL_NOTE_DAYS = 14;

export function licenceCheck(licence: Summary | null, now = Date.now()): SourceCheck {
  const found: SourceCheck["found"] = [];
  const error = licence?.error;
  const status = licence?.status;
  if (status === "expired" && licence?.kind === "trial") found.push(["problem", t("checks.extensions.trialEnded")]);
  else if (status === "expired") found.push(["problem", error ? t("checks.extensions.expiredWhy", { error }) : t("checks.extensions.expired")]);
  else if (status === "invalid") found.push(["problem", error ? t("checks.extensions.invalidWhy", { error }) : t("checks.extensions.invalid")]);
  else if (status === "lapsed") found.push(["note", t("checks.extensions.lapsed")]);
  else if (status === "active" && error) found.push(["note", t("checks.extensions.renewFailed", { error })]);
  const names = licence?.extensions.map((x) => x.name) ?? [];
  const trials = licence?.trials ?? [];
  const over = trials.filter((x) => x.status !== "active" && x.end !== null && now - x.end * 1000 < TRIAL_NOTE_DAYS * 86_400_000);
  if (over.length) found.push(["note", t("checks.extensions.trialOver", { names: over.map((x) => x.name).join(", ") })]);
  const trying = trials.filter((x) => x.status === "active" && x.end !== null)
    .map((x) => t("checks.extensions.tryingOne", { name: x.name, n: daysLeft(x.end!, now) }));
  // paid and installer licences keep loading what is installed after their renewal date, or once ended
  const loads = status === "active" || status === "lapsed" || status === "ended";
  const renew = status === "expired" || status === "invalid" || status === "lapsed" || (status === "active" && !!error);
  const ok = (!loads ? (trying.length ? "" : t("checks.extensions.none"))
    : status === "ended" ? t("checks.extensions.ended")
    : names.length ? t("checks.extensions.activeWith", { names: names.join(", ") }) : t("checks.extensions.active"))
    + (trying.length ? `${loads ? " " : ""}${t("checks.extensions.trying", { list: trying.join(", ") })}` : "");
  return { found, ok, renew, extras: over.length > 0 };
}
