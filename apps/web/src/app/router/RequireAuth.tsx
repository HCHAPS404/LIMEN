import { useTranslation } from "react-i18next";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { LimenMark } from "../../components/brand/Logo";
import { useAuth } from "../providers/AuthProvider";

/** Gate for every client-owned surface. The workspace reads and writes clinical
 *  documents, so it never renders before the session is known (ADR-0004). */
export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();
  const { t } = useTranslation("auth");

  if (status === "loading") {
    return (
      <div
        aria-busy="true"
        aria-live="polite"
        className="flex h-dvh flex-col items-center justify-center gap-4"
      >
        <LimenMark size={26} className="animate-pulse" />
        <p className="type-body-s m-0 text-text-3">{t("guard.checking")}</p>
      </div>
    );
  }

  if (status === "anonymous") {
    // `from` lets the login form return the client to the surface they wanted.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
