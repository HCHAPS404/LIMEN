import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { LogOut } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../app/providers/AuthProvider";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { ThemeToggle } from "./ThemeToggle";

function initials(value: string): string {
  const parts = value.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return value.slice(0, 2).toUpperCase() || "··";
}

/** Identity plus the two per-browser preferences, in the one place a client
 *  looks for them. */
export function AccountMenu() {
  const { account, signOut, isSigningOut } = useAuth();
  const { t } = useTranslation("shell");
  const navigate = useNavigate();

  if (!account) return null;
  const label = account.display_name || account.email || "";

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger
        aria-label={t("account.menuLabel")}
        className="inline-flex h-10 items-center gap-2.5 rounded-sm border border-glass-border bg-[var(--glass-surface)] pr-3 pl-1.5 backdrop-blur-[14px] transition-colors duration-[var(--motion-fast)] hover:border-[var(--glass-border-strong)]"
      >
        <span className="inline-flex h-7 w-7 items-center justify-center rounded-xs bg-[var(--glass-highlight)] text-[0.6875rem] font-semibold tracking-[0.04em] text-ice">
          {initials(label)}
        </span>
        <span className="hidden max-w-[12rem] truncate text-[0.8125rem] font-medium text-text-2 sm:inline">
          {label}
        </span>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className="glass-0 z-50 w-[17rem] rounded-md p-2"
        >
          <div className="flex flex-col gap-0.5 px-2.5 py-2">
            <p className="type-eyebrow m-0 text-text-3">
              {t("account.signedInAs")}
            </p>
            <p className="m-0 truncate text-[0.8125rem] text-ice">
              {account.email}
            </p>
          </div>

          <DropdownMenu.Separator className="my-2 h-px bg-[var(--glass-border)]" />

          <div className="flex items-center justify-between gap-2 px-2.5 py-1.5">
            <span className="type-body-s text-text-3">
              {t("account.preferences")}
            </span>
            <div className="flex items-center gap-1.5">
              <LanguageSwitcher />
              <ThemeToggle className="h-8 w-8" />
            </div>
          </div>

          <DropdownMenu.Separator className="my-2 h-px bg-[var(--glass-border)]" />

          <DropdownMenu.Item
            disabled={isSigningOut}
            onSelect={(event) => {
              // The redirect happens after the mutation settles, so the guard
              // never sees a half-cleared cache.
              event.preventDefault();
              void signOut().then(() => navigate("/", { replace: true }));
            }}
            className="flex cursor-default items-center gap-2.5 rounded-sm px-2.5 py-2 text-[0.8125rem] text-text-2 outline-none data-[disabled]:opacity-45 data-[highlighted]:bg-[var(--glass-highlight)] data-[highlighted]:text-ice"
          >
            <LogOut aria-hidden size={15} strokeWidth={1.6} />
            {isSigningOut ? t("account.signingOut") : t("account.signOut")}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
