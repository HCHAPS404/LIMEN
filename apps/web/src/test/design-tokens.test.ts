import { readFileSync, readdirSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const SRC = join(process.cwd(), "src");

/** Color must reach components through tokens only (FRONTEND.md section 33).
 *  Hex literals are allowed exclusively in the token stylesheet. */
const HEX = /#[0-9a-fA-F]{3,8}\b/;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(full);
    return /\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name)
      ? [full]
      : [];
  });
}

describe("design token discipline", () => {
  it("declares no hex colors outside the token stylesheet", () => {
    const offenders = sourceFiles(SRC)
      .map((file) => ({ file, content: readFileSync(file, "utf8") }))
      .filter(({ content }) => HEX.test(content))
      .map(({ file }) => relative(SRC, file));

    expect(offenders).toEqual([]);
  });

  it("never writes a color as an unhinted arbitrary value", () => {
    // Tailwind resolves `text-[var(--x)]` as a font size, silently dropping the
    // color. Colors must go through named utilities from the theme bridge.
    const offenders = sourceFiles(SRC)
      .map((file) => ({ file, content: readFileSync(file, "utf8") }))
      .filter(({ content }) => /text-\[var\(/.test(content))
      .map(({ file }) => relative(SRC, file));

    expect(offenders).toEqual([]);
  });

  it("defines every theme-scoped token in both light and dark", () => {
    // A token declared for one ground only would silently inherit the other
    // theme's value, which is how contrast regressions get shipped.
    const tokens = readFileSync(join(SRC, "styles", "tokens.css"), "utf8");
    const blocks = tokens.split(/\[data-theme="light"\]\s*\{/);
    expect(blocks).toHaveLength(2);

    const declared = (block: string) =>
      new Set(
        [...block.matchAll(/(--(?:limen|glass|shadow|atmo)-[\w-]+)\s*:/g)].map(
          (match) => match[1],
        ),
      );

    const dark = declared(blocks[0]);
    const light = declared(blocks[1]);

    expect([...dark].filter((token) => !light.has(token))).toEqual([]);
    expect([...light].filter((token) => !dark.has(token))).toEqual([]);
  });

  it("keeps the canonical palette defined in tokens.css", () => {
    const tokens = readFileSync(join(SRC, "styles", "tokens.css"), "utf8");

    for (const token of [
      "--limen-bg-0",
      "--limen-cyan",
      "--limen-teal",
      "--limen-violet",
      "--limen-green",
      "--limen-amber",
      "--limen-coral",
      "--limen-ice",
      "--limen-voice-patient",
      "--limen-voice-agent",
      "--glass-border",
    ]) {
      expect(tokens).toContain(`${token}:`);
    }
  });
});
