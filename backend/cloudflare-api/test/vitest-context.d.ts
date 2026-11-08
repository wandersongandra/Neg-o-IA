import "vitest";

declare module "vitest" {
  interface ProvidedContext {
    d1Migrations: Array<{ name: string; queries: string[] }>;
  }
}
