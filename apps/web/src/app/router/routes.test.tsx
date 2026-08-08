import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderRoute } from "../../test/renderRoute";
import { setViewportWidth } from "../../test/setup";

const healthPayload = {
  status: "ok",
  version: "0.1.0",
  app_env: "test",
  llm_provider: "stub",
  llm_model: "stub-1",
  database: {
    database: "sqlite",
    schema_version: "1",
    path: "runtime/limen.db",
  },
};

function mockBackend(
  handler: (path: string) => { status: number; body?: unknown },
) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      const { status, body } = handler(path);
      return Promise.resolve(
        new Response(body === undefined ? null : JSON.stringify(body), {
          status,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }),
  );
}

describe("application shell routing", () => {
  beforeEach(() => {
    mockBackend((path) =>
      path.endsWith("/health")
        ? { status: 200, body: healthPayload }
        : { status: 404, body: { detail: "Not Found" } },
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the call surface with the primary navigation", async () => {
    renderRoute("/call");

    expect(
      await screen.findByRole("navigation", { name: "Workspace" }),
    ).toBeInTheDocument();
    // Navigation labels follow the default locale (Spanish).
    expect(
      screen.getByRole("link", { name: "Conocimiento" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /start call/i })).toBeInTheDocument();
  });

  it("reports backend health in the context header", async () => {
    renderRoute("/call");

    expect(await screen.findByText("Connected")).toBeInTheDocument();
    expect(screen.getByText(/API v0\.1\.0/)).toBeInTheDocument();
  });

  it("starts the call with no risk assessed and an empty transcript", async () => {
    renderRoute("/call");

    expect(await screen.findByText("NOT ASSESSED")).toBeInTheDocument();
    expect(screen.getByText(/No turns recorded/i)).toBeInTheDocument();
    expect(screen.getByText(/No clinical state yet/i)).toBeInTheDocument();
  });

  it("moves the live context into a drawer below the desktop breakpoint", async () => {
    setViewportWidth(900);
    renderRoute("/call");

    const openContext = await screen.findByRole("button", {
      name: /open live context/i,
    });
    expect(screen.queryByText("NOT ASSESSED")).not.toBeInTheDocument();

    fireEvent.click(openContext);

    expect(
      await screen.findByRole("dialog", { name: /live context/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("NOT ASSESSED")).toBeInTheDocument();
  });

  it("asks for a call before rendering a trace", async () => {
    renderRoute("/trace");

    expect(await screen.findByText(/Choose a call to audit/i)).toBeInTheDocument();
  });

  it("offers account entry points to a visitor on the landing", async () => {
    renderRoute("/", { account: null });

    expect(
      await screen.findByRole("heading", { level: 1, name: /con la duda a la vista/i }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: /crear cuenta/i }).length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByRole("link", { name: /iniciar sesión/i }).length,
    ).toBeGreaterThanOrEqual(1);
  });

  it("sends a signed-in client straight to the workspace from the landing", async () => {
    renderRoute("/");

    expect(
      await screen.findByRole("heading", { level: 1, name: /con la duda a la vista/i }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: /entrar al workspace/i }).length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.queryByRole("link", { name: /crear cuenta/i }),
    ).not.toBeInTheDocument();
  });

  it("explains an unknown route instead of failing silently", async () => {
    renderRoute("/does-not-exist");

    expect(
      await screen.findByText(/This surface does not exist/i),
    ).toBeInTheDocument();
  });
});

describe("session guard", () => {
  beforeEach(() => {
    mockBackend(() => ({ status: 401, body: { detail: { code: "x" } } }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends a visitor to sign in instead of rendering a clinical surface", async () => {
    renderRoute("/call", { account: null });

    expect(
      await screen.findByRole("heading", { name: /inicia sesión/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /start call/i }),
    ).not.toBeInTheDocument();
  });

  it("keeps the knowledge console behind the guard as well", async () => {
    renderRoute("/knowledge", { account: null });

    expect(
      await screen.findByRole("heading", { name: /inicia sesión/i }),
    ).toBeInTheDocument();
  });

  it("shows the account menu once a session exists", async () => {
    renderRoute("/call");

    expect(
      await screen.findByRole("button", { name: /cuenta/i }),
    ).toBeInTheDocument();
  });
});

describe("settings diagnostics", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows the runtime model reported by the backend", async () => {
    mockBackend((path) =>
      path.endsWith("/health")
        ? { status: 200, body: healthPayload }
        : { status: 404, body: { detail: "Not Found" } },
    );

    renderRoute("/settings");

    expect(await screen.findByText("stub")).toBeInTheDocument();
    expect(screen.getByText("stub-1")).toBeInTheDocument();
    expect(screen.getByText("runtime/limen.db")).toBeInTheDocument();
  });

  it("labels unmeasured telemetry instead of inventing numbers", async () => {
    mockBackend((path) =>
      path.endsWith("/health")
        ? { status: 200, body: healthPayload }
        : { status: 404, body: { detail: "Not Found" } },
    );

    renderRoute("/settings");

    expect(
      await screen.findByText("P50 response latency"),
    ).toBeInTheDocument();
    const cost = screen.getByText("Estimated cost per call").nextElementSibling;
    expect(cost).toHaveTextContent("Unknown");
  });

  it("states that the backend is unreachable when health fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))),
    );

    renderRoute("/settings");

    await waitFor(() =>
      expect(
        screen.getByText(/backend is not reachable/i),
      ).toBeInTheDocument(),
    );
  });
});
