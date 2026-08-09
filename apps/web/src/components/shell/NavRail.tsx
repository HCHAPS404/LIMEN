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

/** Quiet selected pill — weight + tint. No inset ring, no left bar. */
const linkClass = (isActive: boolean, expanded: boolean) =>
  cn(
    "group relative flex items-center rounded-md",
    "transition-[background-color,color] duration-[var(--motion-fast)] ease-[var(--motion-ease)]",
    expanded ? "h-11 gap-3 px-3" : "h-11 w-11 justify-center px-0",
    isActive
      ? "bg-[color-mix(in_oklab,var(--limen-ice)_8%,transparent)] text-ice"
      : "text-text-2 hover:bg-[color-mix(in_oklab,var(--limen-ice)_4%,transparent)] hover:text-ice",
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
          <Icon
            aria-hidden
            size={expanded ? 18 : 20}
            strokeWidth={isActive ? 1.9 : 1.6}
            className={cn(
              "shrink-0 transition-colors duration-[var(--motion-fast)]",
              isActive
                ? "text-cyan"
                : "text-text-3 group-hover:text-text-2",
            )}
          />
          {expanded && (
            <span
              className={cn(
                "type-body truncate tracking-[-0.014em]",
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
        "relative hidden shrink-0 flex-col md:flex",
        "bg-[color-mix(in_oklab,var(--limen-bg-1)_18%,transparent)] backdrop-blur-[18px]",
        "transition-[width] duration-[var(--motion-base)] ease-[var(--motion-ease)]",
        railExpanded
          ? "w-[var(--rail-width)]"
          : "w-[var(--rail-width-collapsed)]",
      )}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-y-0 right-0 w-px bg-[linear-gradient(180deg,transparent_6%,color-mix(in_oklab,var(--limen-ice)_10%,transparent)_22%,color-mix(in_oklab,var(--limen-ice)_8%,transparent)_78%,transparent_94%)]"
      />

      <div
        className={cn(
          "relative z-[1] flex min-h-0 flex-1 flex-col",
          railExpanded ? "px-3 pt-5 pb-4" : "items-center px-2.5 pt-5 pb-4",
        )}
      >
        {railExpanded ? (
          <div className="mb-7 flex items-center gap-2.5 px-2.5">
            <LimenMark size={18} />
            <span className="type-eyebrow m-0 text-ice">LIMEN</span>
          </div>
        ) : (
          <div className="mb-7 flex h-11 w-11 items-center justify-center">
            <LimenMark size={20} />
          </div>
        )}

        <ul
          className={cn(
            "m-0 flex list-none flex-col p-0",
            railExpanded ? "gap-1" : "items-center gap-3",
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
            "mt-auto flex flex-col",
            railExpanded ? "gap-2 pt-5" : "items-center gap-3 pt-5",
          )}
        >
          <div
            aria-hidden
            className={cn(
              "mb-1 h-px w-full bg-[linear-gradient(90deg,transparent,color-mix(in_oklab,var(--limen-ice)_10%,transparent)_35%,color-mix(in_oklab,var(--limen-ice)_10%,transparent)_65%,transparent)]",
              !railExpanded && "w-8",
            )}
          />
          <div className={railExpanded ? undefined : "flex justify-center"}>
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
              className={railExpanded ? undefined : "h-11 w-11"}
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
        "bg-[color-mix(in_oklab,var(--limen-bg-1)_40%,transparent)] backdrop-blur-[20px]",
        "shadow-[0_-1px_0_color-mix(in_oklab,var(--limen-ice)_8%,transparent)]",
      )}
    >
      {navItems.map(({ to, labelKey, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              "flex min-h-[3.25rem] flex-1 flex-col items-center justify-center gap-1.5 rounded-md px-1 py-1.5",
              "transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease)]",
              isActive
                ? "bg-[color-mix(in_oklab,var(--limen-ice)_8%,transparent)] text-ice"
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
                className={isActive ? "text-cyan" : undefined}
              />
              <span
                className={cn(
                  "type-label !tracking-[0.06em]",
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
