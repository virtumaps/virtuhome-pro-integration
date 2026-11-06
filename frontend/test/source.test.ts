import { afterEach, describe, expect, it, vi } from "vitest";
import type { ExtensionSource, Hass } from "../src/types";

afterEach(() => vi.unstubAllGlobals());

async function register(queue: unknown) {
  vi.resetModules();
  vi.stubGlobal("window", { virtuhomeSources: queue });
  await import("../src/index");
  return (window as unknown as { virtuhomeSources: unknown }).virtuhomeSources;
}

describe("the source VirtuHome Pro registers with VirtuHome", () => {
  it("queues itself before VirtuHome loads, and registers at once after", async () => {
    const queued = (await register(undefined)) as ExtensionSource[];
    expect(queued.map((s) => s.id)).toEqual(["virtuhome_pro"]);
    const push = vi.fn();
    await register({ push, apiVersion: 5 });
    expect(push).toHaveBeenCalledWith(expect.objectContaining({ id: "virtuhome_pro", automations: "virtuhome_pro/automations" }));
  });

  it("lists the extensions the integration serves, each loaded from its own address", async () => {
    const [source] = (await register(undefined)) as ExtensionSource[];
    const calls: Record<string, unknown>[] = [];
    const hass = {
      callWS: async (msg: Record<string, unknown>) => {
        calls.push(msg);
        return [{ id: "energy", name: "Energy", version: "1.2.0", url: "/virtuhome_ext/energy-1.2.0.js" }];
      },
    } as unknown as Hass;
    const list = await source.extensions(hass);
    expect(calls).toEqual([{ type: "virtuhome_pro/extensions" }]);
    expect(list.map(({ id, name, version }) => ({ id, name, version }))).toEqual([{ id: "energy", name: "Energy", version: "1.2.0" }]);
    expect(typeof list[0].load).toBe("function");
  });
});
