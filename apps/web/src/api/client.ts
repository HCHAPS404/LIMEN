/** Single HTTP entry point for the FastAPI backend.
 *  Errors keep their status so screens can explain what actually failed
 *  instead of rendering a generic message (FRONTEND.md section 30). */

export const API_BASE: string = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  readonly status: number;
  readonly path: string;
  readonly detail?: string;
  /** Stable identifier from the backend (`invalid_credentials`, `email_taken`, …).
   *  Screens localise on the code instead of parsing the English message. */
  readonly code?: string;

  constructor(
    message: string,
    status: number,
    path: string,
    detail?: string,
    code?: string,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.path = path;
    this.detail = detail;
    this.code = code;
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /** The endpoint is not part of the running backend yet. Callers render an
   *  explicit "not available" state rather than inventing data. */
  get isNotImplemented(): boolean {
    return this.status === 404 || this.status === 501;
  }

  get isNetworkFailure(): boolean {
    return this.status === 0;
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "DELETE" | "PATCH";
  body?: BodyInit | null;
  headers?: Record<string, string>;
  signal?: AbortSignal;
};

type Failure = { detail?: string; code?: string };

async function readFailure(response: Response): Promise<Failure> {
  try {
    const text = await response.text();
    if (!text) return {};
    try {
      const parsed = JSON.parse(text) as { detail?: unknown };
      if (typeof parsed.detail === "string") return { detail: parsed.detail };
      // Domain errors answer with `{ detail: { code, message } }`.
      if (parsed.detail && typeof parsed.detail === "object") {
        const shape = parsed.detail as { code?: unknown; message?: unknown };
        return {
          code: typeof shape.code === "string" ? shape.code : undefined,
          detail: typeof shape.message === "string" ? shape.message : undefined,
        };
      }
    } catch {
      // Non-JSON error body: surface the raw text.
    }
    return { detail: text.slice(0, 400) };
  } catch {
    return {};
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body = null, headers = {}, signal } = options;

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      body,
      headers,
      signal,
      // The session lives in an httpOnly cookie, so every request must carry it.
      credentials: "include",
    });
  } catch (cause) {
    throw new ApiError(
      "The LIMEN backend is not reachable.",
      0,
      path,
      cause instanceof Error ? cause.message : undefined,
    );
  }

  if (!response.ok) {
    const failure = await readFailure(response);
    throw new ApiError(
      `Request to ${path} failed with status ${response.status}.`,
      response.status,
      path,
      failure.detail,
      failure.code,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function apiJson<T>(
  path: string,
  payload: unknown,
  method: "POST" | "PATCH" = "POST",
): Promise<T> {
  return apiRequest<T>(path, {
    method,
    body: JSON.stringify(payload),
    headers: { "Content-Type": "application/json" },
  });
}

/** Human-readable message for any thrown value, with backend detail when present. */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.isNetworkFailure) {
      return "The LIMEN backend is not reachable. Start the API with `make run-api` and retry.";
    }
    if (error.isNotImplemented) {
      return `The backend does not expose ${error.path} yet.`;
    }
    return error.detail ? `${error.message} ${error.detail}` : error.message;
  }
  if (error instanceof Error) return error.message;
  return "Unrecognized failure.";
}
