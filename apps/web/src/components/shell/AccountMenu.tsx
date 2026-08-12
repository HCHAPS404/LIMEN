import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ChevronDown, LogOut } from "lucide-react";
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
        className="group inline-flex h-10 items-center gap-2.5 rounded-md border border-[color-mix(in_oklab,var(--limen-ice)_28%,transparent)] bg-[color-mix(in_oklab,var(--limen-bg-2)_50%,transparent)] pr-2.5 pl-1.5 transition-[border-color,background-color] duration-[var(--motion-fast)] hover:border-[color-mix(in_oklab,var(--limen-ice)_40%,transparent)] hover:bg-[color-mix(in_oklab,var(--limen-bg-2)_68%,transparent)] data-[state=open]:border-cyan data-[state=open]:bg-[color-mix(in_oklab,var(--limen-bg-2)_72%,transparent)]"
      >
        <span className="type-label inline-flex h-7 w-7 items-center justify-center rounded-sm bg-[color-mix(in_oklab,var(--limen-cyan)_18%,transparent)] !tracking-[0.04em] text-cyan">
          {initials(label)}
        </span>
        <span className="type-body-s hidden max-w-[11rem] truncate font-medium text-ice sm:inline">
          {label}
        </span>
        <ChevronDown
          aria-hidden
          size={14}
          strokeWidth={1.75}
          className="hidden text-text-3 transition-transform duration-[var(--motion-fast)] group-data-[state=open]:rotate-180 sm:block"
        />
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={10}
          className="glass-1 z-50 w-[17.5rem] rounded-md border border-[color-mix(in_oklab,var(--limen-ice)_22%,transparent)] p-2"
        >
          <div className="flex flex-col gap-0.5 px-2.5 py-2.5">
            <p className="type-eyebrow m-0 text-text-3">
              {t("account.signedInAs")}
            </p>
            <p className="type-body-s m-0 truncate text-ice">{account.email}</p>
          </div>

          <DropdownMenu.Separator className="my-2 h-px bg-[color-mix(in_oklab,var(--limen-ice)_22%,transparent)]" />

          <div className="flex items-center justify-between gap-2 px-2.5 py-1.5">
            <span className="type-body-s text-text-3">
              {t("account.preferences")}
            </span>
            <div className="flex items-center gap-1.5">
              <LanguageSwitcher />
              <ThemeToggle className="h-8 w-8" />
            </div>
          </div>

          <DropdownMenu.Separator className="my-2 h-px bg-[color-mix(in_oklab,var(--limen-ice)_22%,transparent)]" />

          <DropdownMenu.Item
            disabled={isSigningOut}
            onSelect={(event) => {
              event.preventDefault();
              void signOut().then(() => navigate("/", { replace: true }));
            }}
            className="type-body-s flex cursor-default items-center gap-2.5 rounded-sm px-2.5 py-2.5 text-text-2 outline-none data-[disabled]:opacity-45 data-[highlighted]:bg-[var(--glass-highlight)] data-[highlighted]:text-ice"
          >
            <LogOut aria-hidden size={15} strokeWidth={1.6} />
            {isSigningOut ? t("account.signingOut") : t("account.signOut")}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
