// What VirtuHome's extension API (virtuhome/frontend/src/ext/api.ts) expects from a source. Kept as a
// copy here: VirtuHome Pro has no build-time link to VirtuHome.

/** The part of Home Assistant's frontend object this module uses. */
export interface Hass {
  callWS<T>(msg: Record<string, unknown>): Promise<T>;
  language?: string;
  locale?: { language?: string };
}

export interface SourceExtension {
  id: string;
  name: string;
  version: string;
  load(): Promise<unknown>;
}

export interface SourceCheck {
  found: ["problem" | "note", string][];
  ok: string;
  renew?: boolean;
  extras?: boolean;
}

export interface ExtensionSource {
  id: string;
  name: string;
  extensions(hass: Hass): Promise<SourceExtension[]>;
  automations?: string;
  extras?(el: HTMLElement, hass: Hass): void;
  check?(hass: Hass): Promise<SourceCheck>;
  renew?(hass: Hass): Promise<void>;
}

/** virtuhome_pro/licence/* answers. status: none, active, lapsed, ended, expired or invalid. */
export interface Trial {
  id: string;
  name: string;
  version: string | null;
  /** unix seconds */
  end: number | null;
  status: string;
}

export interface Summary {
  status: string;
  kind?: string | null;
  error: string | null;
  key_hint: string | null;
  extensions: { id: string; name: string; version: string }[];
  trials?: Trial[];
}

/** virtuhome_pro/catalog: what can be bought or tried (buy links only once the shop is open). */
export type Catalog = { id: string; name: string; description?: string; price?: string; checkout_url?: string; trial_days?: number }[];
