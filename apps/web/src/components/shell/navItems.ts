import { Mic, Radar, ScrollText, Settings2, Waypoints } from "lucide-react";
import type { ComponentType } from "react";

import type { ShellKey } from "../../i18n/keys";

export type NavItem = {
  to: string;
  /** Key in the `shell` namespace; the rail resolves it per locale. */
  labelKey: ShellKey;
  icon: ComponentType<{
    size?: number;
    strokeWidth?: number;
    className?: string;
    "aria-hidden"?: boolean;
  }>;
};

/** Primary workspace surfaces — stay together at the top of the rail. */
export const primaryNavItems: NavItem[] = [
  { to: "/call", labelKey: "nav.call", icon: Mic },
  { to: "/knowledge", labelKey: "nav.knowledge", icon: Radar },
  { to: "/trace", labelKey: "nav.trace", icon: Waypoints },
  { to: "/sessions", labelKey: "nav.sessions", icon: ScrollText },
];

/** Pinned to the bottom of the rail in both expanded and collapsed modes. */
export const settingsNavItem: NavItem = {
  to: "/settings",
  labelKey: "nav.settings",
  icon: Settings2,
};

/** Flat list for mobile and any consumer that needs every destination. */
export const navItems: NavItem[] = [...primaryNavItems, settingsNavItem];
