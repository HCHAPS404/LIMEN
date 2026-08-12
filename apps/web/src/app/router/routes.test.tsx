import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { renderRoute } from "../../test/renderRoute";
import { setViewportWidth } from "../../test/setup";
import { useCallStore } from "../../state/call-store";

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
      await screen.findByRole("navigation", { name: /espacio de trabajo|workspace/i }),
    ).toBeInTheDocument();
    // Navigation labels follow the default locale (Spanish).
    expect(
      screen.getByRole("link", { name: "Conocimiento" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Ir a la landing de LIMEN|Go to LIMEN landing/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /iniciar llamada|start call/i }),
    ).toBeInTheDocument();
  });

  it("reports backend health on Settings, not as a global Connected claim", async () => {
    renderRoute("/settings");

    expect(await screen.findByText(/API activa|API up/i)).toBeInTheDocument();
    expect(screen.getByText(/API v0\.1\.0/)).toBeInTheDocument();
  });

  it("keeps the call stage alone until a session starts", async () => {
    renderRoute("/call");

    expect(
      await screen.findByRole("button", { name: /iniciar llamada|start call/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/NOT ASSESSED|SIN EVALUAR/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/sin turnos|no turns/i)).not.toBeInTheDocument();
  });

  it("reveals live context and transcript as their own sections after start", async () => {
    setViewportWidth(900);
    mockBackend((path) => {
      if (path.endsWith("/health")) return { status: 200, body: healthPayload };
      if (path.endsWith("/api/calls") && !path.includes("/stream")) {
        return {
          status: 201,
          body: {
            call_id: "call-test",
            patient_alias: "Paciente",
            started_at: "2026-08-07T12:00:00Z",
            final_risk: null,
            escalated: false,
          },
        };
      }
      return { status: 404, body: { detail: "Not Found" } };
    });

    class MockWebSocket {
      static OPEN = 1;
      readyState = 1;
      binaryType = "arraybuffer";
      onopen: ((ev: Event) => void) | null = null;
      onerror: ((ev: Event) => void) | null = null;
      onclose: ((ev: CloseEvent) => void) | null = null;
      onmessage: ((ev: MessageEvent) => void) | null = null;
      constructor() {
        queueMicrotask(() => this.onopen?.(new Event("open")));
      }
      send() {}
      close() {
        this.readyState = 3;
        this.onclose?.(new CloseEvent("close"));
      }
    }
    vi.stubGlobal("WebSocket", MockWebSocket);

    // jsdom has no mic: stub just enough Web Audio + getUserMedia for session.start().
    const fakeTrack = { stop: () => undefined, enabled: true } as MediaStreamTrack;
    const fakeStream = {
      getTracks: () => [fakeTrack],
      getAudioTracks: () => [fakeTrack],
    } as MediaStream;
    vi.stubGlobal(
      "navigator",
      {
        ...navigator,
        mediaDevices: {
          getUserMedia: vi.fn(async () => fakeStream),
          enumerateDevices: vi.fn(async () => []),
        },
      } as unknown as Navigator,
    );
    class FakeAudioContext {
      state = "running";
      destination = {};
      sampleRate = 48000;
      currentTime = 0;
      createMediaStreamSource() {
        return { connect: () => undefined, disconnect: () => undefined };
      }
      createAnalyser() {
        return {
          fftSize: 2048,
          smoothingTimeConstant: 0.38,
          frequencyBinCount: 1024,
          connect: () => undefined,
          disconnect: () => undefined,
          getFloatTimeDomainData: (buf: Float32Array) => buf.fill(0),
        };
      }
      createGain() {
        return {
          gain: { value: 0 },
          connect: () => undefined,
          disconnect: () => undefined,
        };
      }
      createOscillator() {
        return {
          type: "sine",
          frequency: { value: 440 },
          connect: () => undefined,
          start: () => undefined,
          stop: () => undefined,
        };
      }
      createScriptProcessor() {
        return {
          onaudioprocess: null as ((ev: unknown) => void) | null,
          connect: () => undefined,
          disconnect: () => undefined,
        };
      }
      resume = async () => undefined;
      close = async () => undefined;
    }
    vi.stubGlobal("AudioContext", FakeAudioContext);
    vi.stubGlobal("webkitAudioContext", FakeAudioContext);

    renderRoute("/call");

    fireEvent.click(
      await screen.findByRole("button", { name: /iniciar llamada|start call/i }),
    );

    await waitFor(() => {
      expect(["LISTENING", "SPEAKING", "ERROR"]).toContain(
        useCallStore.getState().phase,
      );
    });
    expect(
      await screen.findByText(/contexto en vivo|live context/i, {}, { timeout: 3000 }),
    ).toBeInTheDocument();
    expect(screen.getByText(/sin turnos|no turns/i)).toBeInTheDocument();
    expect(
      screen.getAllByText(
        /aún no hay decisión|no safety decision|sin evaluar|unassessed/i,
      ).length,
    ).toBeGreaterThan(0);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("asks for a call before rendering a trace", async () => {
    renderRoute("/trace");

    expect(
      await screen.findByText(/elige una llamada|choose a call/i),
    ).toBeInTheDocument();
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

  it("keeps preference actions in one panel with sign out last", async () => {
    mockBackend((path) =>
      path.endsWith("/health")
        ? { status: 200, body: healthPayload }
        : { status: 404, body: { detail: "Not Found" } },
    );

    renderRoute("/settings");

    expect(
      await screen.findByRole("button", { name: /borrar cuenta|delete account/i }),
    ).toBeInTheDocument();
    const signOut = screen.getByRole("button", {
      name: /cerrar sesión|sign out/i,
    });
    expect(signOut).toBeInTheDocument();
    // Sign out is the last actionable control in the session block.
    expect(signOut.compareDocumentPosition(
      screen.getByRole("button", { name: /borrar cuenta|delete account/i }),
    ) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy();
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
