import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

/** Dark is the product default: the clinical workspace is used in low light and
 *  the voice sphere is designed against a dark canvas. Light is opt-in and
 *  remembered per browser (FRONTEND.md section 9). */
export type Theme = "dark" | "light";

export const THEME_STORAGE_KEY = "limen.theme";
export const DEFAULT_THEME: Theme = "dark";

type ThemeContextValue = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function isTheme(value: string | null): value is Theme {
  return value === "dark" || value === "light";
}

export function readStoredTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isTheme(stored) ? stored : DEFAULT_THEME;
  } catch {
    // Private browsing or a blocked storage partition: fall back, never throw.
    return DEFAULT_THEME;
  }
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(readStoredTheme);

  useEffect(() => {
    applyTheme(theme);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // Preference stays session-only when storage is unavailable.
    }
  }, [theme]);

  return (
    <ThemeContext.Provider
      value={{
        theme,
        setTheme,
        toggleTheme: () =>
          setTheme((current) => (current === "dark" ? "light" : "dark")),
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used inside ThemeProvider.");
  }
  return context;
}
