import { Moon, Sun } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useTheme } from "../../app/providers/ThemeProvider";
import { IconButton } from "../primitives/IconButton";

/** Single control, no dropdown: there are exactly two grounds. */
export function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();
  const { t } = useTranslation("common");

  return (
    <IconButton
      className={className}
      label={theme === "dark" ? t("theme.toLight") : t("theme.toDark")}
      onClick={toggleTheme}
      icon={
        theme === "dark" ? (
          <Sun aria-hidden size={18} strokeWidth={1.6} />
        ) : (
          <Moon aria-hidden size={18} strokeWidth={1.6} />
        )
      }
    />
  );
}
