// The few Node file functions the tests use (the project has no Node types).
declare module "node:fs" {
  export function readFileSync(path: string, encoding: "utf8"): string;
  export function readdirSync(path: string): string[];
  export function readdirSync(path: string, options: { recursive: true }): string[];
  export function statSync(path: string): { size: number };
}

