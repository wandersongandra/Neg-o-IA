import { readFile, readdir } from "node:fs/promises";

export default async function setup({ provide }: { provide: (key: string, value: unknown) => void }) {
  const directory = new URL("../migrations/", import.meta.url);
  const files = (await readdir(directory)).filter((file) => file.endsWith(".sql")).sort();
  const migrations = await Promise.all(files.map(async (name) => {
    const source = await readFile(new URL(name, directory), "utf8");
    return { name, queries: source.split(";").map((query) => query.trim()).filter(Boolean) };
  }));
  provide("d1Migrations", migrations);
}
