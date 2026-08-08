import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import i18n, {
  DEFAULT_LOCALE,
  LOCALE_STORAGE_KEY,
  setLocale,
} from "../../i18n";
import { LanguageSwitcher } from "../../components/shell/LanguageSwitcher";
import { ThemeToggle } from "../../components/shell/ThemeToggle";
import { renderWithProviders } from "../../test/renderRoute";
import { THEME_STORAGE_KEY } from "./ThemeProvider";

describe("theme preference", () => {
  beforeEach(() => {
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
  });

  it("starts dark and remembers a switch to light", async () => {
    renderWithProviders(<ThemeToggle />);

    await waitFor(() =>
      expect(document.documentElement.dataset.theme).toBe("dark"),
    );

    fireEvent.click(screen.getByRole("button"));

    await waitFor(() =>
      expect(document.documentElement.dataset.theme).toBe("light"),
    );
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
  });

  it("restores a stored light preference on mount", async () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");
    renderWithProviders(<ThemeToggle />);

    await waitFor(() =>
      expect(document.documentElement.dataset.theme).toBe("light"),
    );
  });

  it("labels the control by the theme it switches to", () => {
    renderWithProviders(<ThemeToggle />);
    expect(
      screen.getByRole("button", { name: /tema claro/i }),
    ).toBeInTheDocument();
  });
});

describe("locale preference", () => {
  afterEach(async () => {
    window.localStorage.clear();
    await setLocale(DEFAULT_LOCALE);
  });

  it("defaults to Spanish", () => {
    expect(i18n.resolvedLanguage).toBe("es");
  });

  it("switches interface copy to English and remembers it", async () => {
    renderWithProviders(<LanguageSwitcher />);

    fireEvent.click(screen.getByRole("button", { name: "en" }));

    await waitFor(() => expect(i18n.resolvedLanguage).toBe("en"));
    expect(i18n.t("shell:nav.knowledge")).toBe("Knowledge");
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("en");
    expect(document.documentElement.lang).toBe("en");
  });

  it("keeps clinical vocabulary out of the translation tables", () => {
    // GREEN / UNKNOWN and other backend enums must never be translated.
    const tables = JSON.stringify(i18n.store.data);
    for (const value of ["GREEN", "AMBER", "RED", "UNKNOWN", "CONFLICTING"]) {
      expect(tables).not.toContain(value);
    }
  });
});
