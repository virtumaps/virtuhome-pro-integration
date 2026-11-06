import { describe, expect, it } from "vitest";
import { licenceCheck } from "../src/check";
import { daysLeft } from "../src/dom";
import type { Summary } from "../src/types";

const base = (s: Partial<Summary>): Summary => ({ status: "none", error: null, key_hint: null, extensions: [], ...s });

describe("what VirtuHome Pro says in Check my setup", () => {
  it("a licence active, expired or unable to renew", () => {
    const active = base({ status: "active", extensions: [{ id: "wall_tablet", name: "Wall Tablet", version: "1.1.0" }] });
    expect(licenceCheck(active)).toEqual({ found: [], ok: "Licence active: Wall Tablet.", renew: false, extras: false });
    expect(licenceCheck({ ...active, status: "expired", error: "token expired" })).toMatchObject({ found: [["problem", expect.stringContaining("token expired")]], renew: true });
    expect(licenceCheck({ ...active, error: "could not reach the licence server" })).toMatchObject({ found: [["note", expect.any(String)]], renew: true });
    expect(licenceCheck(base({}))).toEqual({ found: [], ok: "No licence key, so no extensions.", renew: false, extras: false });
    expect(licenceCheck(null).ok).toBe("No licence key, so no extensions.");
  });

  it("trials beside the licence, and a note for a while after one ends", () => {
    const now = Date.UTC(2026, 10, 6);
    const day = 86_400_000;
    const trial = (status: string, endIn: number) => ({ id: "security", name: "Security", version: "1.3.0", status, end: (now + endIn) / 1000 });
    expect(daysLeft(now / 1000 + 9.2 * day / 1000, now)).toBe(10);
    expect(daysLeft(now / 1000 - day / 1000, now)).toBe(0);
    expect(licenceCheck(base({ trials: [trial("active", 9.5 * day)] }), now)).toMatchObject({ found: [], ok: "Trying Security (10 days left)." });
    const active = base({ status: "active", extensions: [{ id: "energy", name: "Energy", version: "1.2.0" }], trials: [trial("active", 0.5 * day)] });
    expect(licenceCheck(active, now).ok).toBe("Licence active: Energy. Trying Security (1 day left).");
    const over = licenceCheck(base({ trials: [trial("expired", -2 * day)] }), now);
    expect(over).toMatchObject({ found: [["note", expect.stringContaining("Security")]], extras: true });
    expect(licenceCheck(base({ trials: [trial("expired", -20 * day)] }), now)).toMatchObject({ found: [], extras: false });
  });

  it("what was bought keeps working past the renewal date; a trial stops", () => {
    const paid = base({ status: "lapsed", kind: "paid", extensions: [{ id: "security", name: "Security", version: "1.3.0" }] });
    expect(licenceCheck(paid)).toMatchObject({ found: [["note", expect.stringContaining("installed extensions keep working")]], renew: true });
    expect(licenceCheck({ ...paid, status: "ended", kind: "installer" })).toMatchObject({ found: [], renew: false, ok: expect.stringContaining("keep working") });
    expect(licenceCheck({ ...paid, status: "expired", kind: "trial" })).toMatchObject({
      found: [["problem", "The trial has ended, so its extensions have stopped."]],
    });
  });
});
