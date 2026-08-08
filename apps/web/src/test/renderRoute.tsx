import { QueryClient } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";

import { authKeys, type AccountResponse } from "../api/auth";
import { AppProviders } from "../app/providers/AppProviders";
import { routes } from "../app/router/routes";

/** Retries are disabled so failed-request states assert immediately. */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

export const testAccount: AccountResponse = {
  account_id: "acc-test",
  email: "clinica@umbral.io",
  display_name: "Clínica Umbral",
  created_at: "2026-01-04T09:00:00Z",
};

type RenderRouteOptions = {
  /** `null` renders as a visitor, which the route guard redirects to `/login`. */
  account?: AccountResponse | null;
};

export function renderRoute(
  initialPath: string,
  { account = testAccount }: RenderRouteOptions = {},
): RenderResult {
  const router = createMemoryRouter(routes, {
    initialEntries: [initialPath],
  });

  const client = createTestQueryClient();
  // Seeding the session keeps workspace tests focused on their own surface
  // instead of replaying a login through the guard.
  if (account) client.setQueryData(authKeys.me, account);

  return render(
    <AppProviders client={client}>
      <RouterProvider router={router} />
    </AppProviders>,
  );
}

/** Renders a single component inside the app providers, without routing. */
export function renderWithProviders(ui: ReactElement): RenderResult {
  const client = createTestQueryClient();
  client.setQueryData(authKeys.me, testAccount);
  return render(<AppProviders client={client}>{ui}</AppProviders>);
}
