import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { App } from "./App";

function renderApp(path = "/call") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("App shell", () => {
  it("renders LIMEN brand and call route", () => {
    renderApp("/call");
    expect(screen.getByText(/LIMEN/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Llamada/i })).toBeInTheDocument();
  });

  it("renders settings diagnostics route", () => {
    renderApp("/settings");
    expect(screen.getByRole("heading", { name: /Ajustes/i })).toBeInTheDocument();
  });
});
