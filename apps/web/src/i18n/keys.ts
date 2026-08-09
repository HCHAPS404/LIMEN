import type { ParseKeys } from "i18next";

/** Key aliases for values passed across module boundaries (route metadata, nav
 *  items, error mappers). Using them keeps a renamed key a compile error rather
 *  than a raw key rendered on screen. */
export type CommonKey = ParseKeys<"common">;
export type ShellKey = ParseKeys<"shell">;
export type LandingKey = ParseKeys<"landing">;
export type AuthKey = ParseKeys<"auth">;
