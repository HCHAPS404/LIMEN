import { ApiError } from "../../api/client";
import type { AuthKey } from "../../i18n/keys";

/** Maps a backend failure onto a translation key.
 *  The English text from the API is never shown: the UI is bilingual and the
 *  backend `code` is the stable contract. */
export function authErrorKey(error: unknown): AuthKey {
  if (error instanceof ApiError) {
    if (error.isNetworkFailure) return "errors.unreachable";
    switch (error.code) {
      case "invalid_credentials":
        return "errors.invalidCredentials";
      case "email_taken":
        return "errors.emailTaken";
      case "weak_password":
        return "errors.passwordLength";
      case "invalid_email":
        return "errors.email";
      default:
        return "errors.generic";
    }
  }
  return "errors.generic";
}
