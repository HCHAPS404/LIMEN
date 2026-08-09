import type { es } from "./locales/es";

/** Binds `t()` to the Spanish key tree so a typo in a key fails typecheck. */
declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "common";
    resources: typeof es;
  }
}
