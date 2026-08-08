import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../../app/providers/AuthProvider";
import type { AuthKey } from "../../i18n/keys";
import { Button } from "../../components/primitives/Button";
import { TextField } from "../../components/primitives/TextField";
import { AuthError, AuthLayout } from "./AuthLayout";
import { authErrorKey } from "./authError";

/** Mirrors `MINIMUM_PASSWORD_LENGTH` in limen/auth/passwords.py so the form can
 *  say what is wrong before a round trip. The backend remains authoritative. */
const MINIMUM_PASSWORD_LENGTH = 10;

export function RegisterPage() {
  const { t } = useTranslation("auth");
  const { signUp } = useAuth();
  const navigate = useNavigate();

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorKey, setErrorKey] = useState<AuthKey | null>(null);
  const [passwordErrorKey, setPasswordErrorKey] = useState<AuthKey | null>(
    null,
  );
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorKey(null);
    setPasswordErrorKey(null);

    if (!email.trim() || !password) {
      setErrorKey("errors.required");
      return;
    }
    if (password.length < MINIMUM_PASSWORD_LENGTH) {
      setPasswordErrorKey("errors.passwordLength");
      return;
    }

    setSubmitting(true);
    try {
      await signUp({ email, password, displayName });
      navigate("/call", { replace: true });
    } catch (error) {
      setErrorKey(authErrorKey(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title={t("register.title")}
      subtitle={t("register.subtitle")}
      footer={
        <p className="type-body-s m-0 text-text-3">
          {t("register.hasAccount")}{" "}
          <Link to="/login" className="limen-link font-medium">
            {t("register.signIn")}
          </Link>
        </p>
      }
    >
      <form className="flex flex-col gap-5" onSubmit={submit} noValidate>
        <TextField
          label={t("fields.displayName")}
          autoComplete="organization"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
        />
        <TextField
          label={t("fields.email")}
          type="email"
          autoComplete="email"
          placeholder={t("fields.emailPlaceholder")}
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <TextField
          label={t("fields.password")}
          type="password"
          autoComplete="new-password"
          hint={t("fields.passwordHint")}
          error={passwordErrorKey ? t(passwordErrorKey) : undefined}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {errorKey && <AuthError message={t(errorKey)} />}

        <Button type="submit" variant="inverse" size="lg" loading={submitting}>
          {submitting ? t("register.submitting") : t("register.submit")}
        </Button>
      </form>
    </AuthLayout>
  );
}
