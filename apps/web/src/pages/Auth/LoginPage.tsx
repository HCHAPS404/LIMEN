import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../app/providers/AuthProvider";
import type { AuthKey } from "../../i18n/keys";
import { Button } from "../../components/primitives/Button";
import { TextField } from "../../components/primitives/TextField";
import { AuthError, AuthLayout } from "./AuthLayout";
import { authErrorKey } from "./authError";

export function LoginPage() {
  const { t } = useTranslation("auth");
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/call";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorKey, setErrorKey] = useState<AuthKey | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim() || !password) {
      setErrorKey("errors.required");
      return;
    }

    setErrorKey(null);
    setSubmitting(true);
    try {
      await signIn({ email, password });
      navigate(from, { replace: true });
    } catch (error) {
      setErrorKey(authErrorKey(error));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title={t("login.title")}
      subtitle={t("login.subtitle")}
      footer={
        <p className="type-body-s m-0 text-text-3">
          {t("login.noAccount")}{" "}
          <Link to="/register" className="limen-link font-medium">
            {t("login.createAccount")}
          </Link>
        </p>
      }
    >
      <form className="flex flex-col gap-5" onSubmit={submit} noValidate>
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
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {errorKey && <AuthError message={t(errorKey)} />}

        <Button type="submit" variant="inverse" size="lg" loading={submitting}>
          {submitting ? t("login.submitting") : t("login.submit")}
        </Button>
      </form>
    </AuthLayout>
  );
}
