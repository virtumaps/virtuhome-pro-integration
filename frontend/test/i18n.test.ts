import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { language, t, useLanguage } from "../src/i18n";

const src = readFileSync(new URL("../src/i18n.ts", import.meta.url).pathname, "utf8");
/** Each table's keys and the placeholders of each text, read from the source. */
function tables(): Record<string, Record<string, string[]>> {
  const out: Record<string, Record<string, string[]>> = {};
  let current = "";
  for (const line of src.split("\n")) {
    const table = /^const (EN|DE|NL)\b/.exec(line);
    if (table) out[(current = table[1])] = {};
    const entry = /^\s*"([\w.]+)": (.*),$/.exec(line);
    if (entry && current) out[current][entry[1]] = [...new Set(entry[2].match(/\{\w+\}/g) ?? [])].sort();
  }
  return out;
}

describe("texts", () => {
  it("German and Dutch have every English text, with the same placeholders", () => {
    const { EN, DE, NL } = tables();
    expect(Object.keys(EN).length).toBeGreaterThan(30);
    for (const other of [DE, NL]) expect(other).toEqual(EN);
  });

  it("uses every text", () => {
    const code = ["index.ts", "check.ts", "extras.ts"].map((f) => readFileSync(new URL(`../src/${f}`, import.meta.url).pathname, "utf8")).join("\n");
    const unused = Object.keys(tables().EN).filter((k) => !code.includes(`"${k}"`));
    expect(unused).toEqual([]);
  });

  it("follows Home Assistant's language, else its main language, else English", () => {
    expect(language({ language: "de" })).toBe("de");
    expect(language({ locale: { language: "nl-BE" } })).toBe("nl");
    expect(language({ language: "fr" })).toBe("en");
    useLanguage({ language: "de" });
    expect(t("editor.extensions.tryItFree", { n: 1 })).toContain("1");
    useLanguage({ language: "en" });
    expect(t("editor.extensions.tryItFree", { n: 14 })).toBe("Try it free for 14 days");
  });
});
