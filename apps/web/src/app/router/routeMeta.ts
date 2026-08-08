import type { ShellKey } from "../../i18n/keys";

/** Route chrome is described by a translation key, not a literal string, so the
 *  header follows the selected locale. Keys live in the `shell` namespace. */
export type RouteMeta = {
  titleKey: ShellKey;
  subtitleKey?: ShellKey;
};
