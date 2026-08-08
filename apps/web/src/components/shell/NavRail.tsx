import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import { cn } from "../../lib/cn";
import { useUiStore } from "../../state/ui-store";
import { LimenMark } from "../brand/Logo";
import { IconButton } from "../primitives/IconButton";
import { Tooltip } from "../primitives/Tooltip";
import {
  navItems,
  primaryNavItems,
  settingsNavItem,
  type NavItem,
} from "./navItems";

const linkClass = (isActive: boolean, expanded: boolean) =>
  cn(
    "group relative flex items-center rounded-sm",
    "transition-[background-color,color] duration-[var(--motion-fast)] ease-[var(--motion-ease)]",
    expanded ? "h-12 gap-3.5 px-3.5" : "h-12 w-12 justify-center px-0",
    isActive
      ? "bg-[var(--glass-highlight)] text-ice"
      : "text-text-2 hover:bg-[var(--glass-highlight)] hover:text-ice",
  );

function NavItemLink({
  to,
  labelKey,
  icon: Icon,
  expanded,
}: {
  to: string;
  labelKey: NavItem["labelKey"];
  icon: NavItem["icon"];
  expanded: boolean;
}) {
  const { t } = useTranslation("shell");
  const label = t(labelKey);

  const link = (
    <NavLink
      to={to}
      aria-label={expanded ? undefined : label}
      className={({ isActive }) => linkClass(isActive, expanded)}
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <span
              aria-hidden
              className={cn(
                "absolute top-1/2 -translate-y-1/2 rounded-full bg-ice",
                expanded ? "left-0 h-6 w-[2px]" : "left-1 h-6 w-[2px]",
              )}
            />
          )}
          <Icon
            aria-hidden
            size={expanded ? 19 : 22}
            strokeWidth={isActive ? 1.85 : 1.6}
            className={cn(
              "shrink-0 transition-colors duration-[var(--motion-fast)]",
              isActive ? "text-ice" : "text-text-3 group-hover:text-text-2",
            )}
          />
          {expanded && (
            <span
              className={cn(
                "truncate text-[0.975rem] tracking-[-0.012em]",
                isActive
                  ? "font-semibold text-ice"
                  : "font-medium text-text-2 group-hover:text-ice",
              )}
            >
              {label}
            </span>
          )}
        </>
      )}
    </NavLink>
  );

  if (expanded) return link;
  return <Tooltip content={label}>{link}</Tooltip>;
}

export function NavRail() {
  const railExpanded = useUiStore((state) => state.railExpanded);
  const toggleRail = useUiStore((state) => state.toggleRail);
  const { t } = useTranslation("shell");

  return (
    <nav
      aria-label={t("workspace")}
      className={cn(
        "hidden shrink-0 flex-col md:flex",
        "border-r border-glass-border",
        "bg-[var(--glass-surface-strong)] backdrop-blur-[32px] saturate-[1.15]",
        "transition-[width] duration-[var(--motion-base)] ease-[var(--motion-ease)]",
        railExpanded
          ? "w-[var(--rail-width)]"
          : "w-[var(--rail-width-collapsed)]",
      )}
    >
      <div
        className={cn(
          "flex min-h-0 flex-1 flex-col",
          railExpanded ? "px-3 pt-5 pb-4" : "items-center px-3 pt-5 pb-4",
        )}
      >
        {railExpanded ? (
          <div className="mb-6 flex items-center gap-2.5 px-3">
            <LimenMark size={18} />
            <span className="type-label m-0 text-text-3">{t("workspace")}</span>
          </div>
        ) : (
          <div className="mb-8 flex h-12 w-12 items-center justify-center">
            <LimenMark size={20} />
          </div>
        )}

        <ul
          className={cn(
            "m-0 flex list-none flex-col p-0",
            railExpanded ? "gap-1.5" : "items-center gap-5",
          )}
        >
          {primaryNavItems.map((item) => (
            <li
              key={item.to}
              className={railExpanded ? undefined : "flex justify-center"}
            >
              <NavItemLink {...item} expanded={railExpanded} />
            </li>
          ))}
        </ul>

        <div
          className={cn(
            "mt-auto flex flex-col border-t border-glass-border",
            railExpanded
              ? "gap-2 px-0 pt-4"
              : "items-center gap-5 pt-5",
          )}
        >
          <div
            className={railExpanded ? undefined : "flex justify-center"}
          >
            <NavItemLink {...settingsNavItem} expanded={railExpanded} />
          </div>
          <div
            className={cn(
              "flex",
              railExpanded ? "justify-end px-1" : "justify-center",
            )}
          >
            <IconButton
              label={railExpanded ? t("rail.collapse") : t("rail.expand")}
              className={railExpanded ? undefined : "h-12 w-12"}
              icon={
                railExpanded ? (
                  <PanelLeftClose aria-hidden size={18} strokeWidth={1.6} />
                ) : (
                  <PanelLeftOpen aria-hidden size={20} strokeWidth={1.6} />
                )
              }
              onClick={toggleRail}
            />
          </div>
        </div>
      </div>
    </nav>
  );
}

/** Mobile equivalent: critical surfaces stay one tap away (section 27). */
export function NavBarMobile() {
  const { t } = useTranslation("shell");

  return (
    <nav
      aria-label={t("workspace")}
      className={cn(
        "fixed inset-x-0 bottom-0 z-30 flex items-stretch justify-around gap-1 px-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-2 md:hidden",
        "border-t border-glass-border bg-[var(--glass-surface-strong)] backdrop-blur-[28px] saturate-[1.15]",
      )}
    >
      {navItems.map(({ to, labelKey, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              "flex min-h-[3.25rem] flex-1 flex-col items-center justify-center gap-1.5 rounded-sm px-1 py-1.5",
              "transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease)]",
              isActive
                ? "bg-[var(--glass-highlight)] text-ice"
                : "text-text-3",
            )
          }
        >
          {({ isActive }) => (
            <>
              <Icon
                aria-hidden
                size={18}
                strokeWidth={isActive ? 1.75 : 1.5}
              />
              <span
                className={cn(
                  "text-[0.625rem] tracking-[0.08em] uppercase",
                  isActive ? "font-semibold text-ice" : "font-medium",
                )}
              >
                {t(labelKey)}
              </span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
