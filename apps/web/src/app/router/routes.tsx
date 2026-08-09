import type { RouteObject } from "react-router-dom";

import { CallPage } from "../../pages/Call/CallPage";
import { KnowledgePage } from "../../pages/Knowledge/KnowledgePage";
import { NotFoundPage } from "../../pages/NotFound/NotFoundPage";
import { SessionsPage } from "../../pages/Sessions/SessionsPage";
import { WorkspaceLayout } from "../layouts/WorkspaceLayout";
import { RequireAuth } from "./RequireAuth";
import { RouteFallback } from "./RouteFallback";
import type { RouteMeta } from "./routeMeta";

const meta = (value: RouteMeta): RouteMeta => value;

export const routes: RouteObject[] = [
  {
    path: "/",
    // The landing surface owns the motion library; keeping it out of the
    // workspace bundle protects voice-path load time (section 31).
    lazy: async () => ({
      Component: (await import("../../pages/Landing/LandingPage")).LandingPage,
    }),
    hydrateFallbackElement: <RouteFallback />,
  },
  {
    path: "/login",
    lazy: async () => ({
      Component: (await import("../../pages/Auth/LoginPage")).LoginPage,
    }),
    hydrateFallbackElement: <RouteFallback />,
  },
  {
    path: "/register",
    lazy: async () => ({
      Component: (await import("../../pages/Auth/RegisterPage")).RegisterPage,
    }),
    hydrateFallbackElement: <RouteFallback />,
  },
  {
    // Every clinical surface sits behind the session guard: the workspace reads
    // and writes documents that belong to one client only (ADR-0004).
    element: <RequireAuth />,
    hydrateFallbackElement: <RouteFallback />,
    children: [
      {
        element: <WorkspaceLayout />,
        children: [
          {
            path: "/call",
            element: <CallPage />,
            handle: meta({
              titleKey: "routes.call.title",
              subtitleKey: "routes.call.subtitle",
            }),
          },
          {
            path: "/knowledge",
            element: <KnowledgePage />,
            handle: meta({
              titleKey: "routes.knowledge.title",
              subtitleKey: "routes.knowledge.subtitle",
            }),
          },
          {
            path: "/trace/:callId?",
            lazy: async () => ({
              Component: (await import("../../pages/Trace/TracePage")).TracePage,
            }),
            handle: meta({
              titleKey: "routes.trace.title",
              subtitleKey: "routes.trace.subtitle",
            }),
          },
          {
            path: "/sessions",
            element: <SessionsPage />,
            handle: meta({
              titleKey: "routes.sessions.title",
              subtitleKey: "routes.sessions.subtitle",
            }),
          },
          {
            path: "/settings",
            lazy: async () => ({
              Component: (await import("../../pages/Settings/SettingsPage"))
                .SettingsPage,
            }),
            handle: meta({
              titleKey: "routes.settings.title",
              subtitleKey: "routes.settings.subtitle",
            }),
          },
          {
            path: "*",
            element: <NotFoundPage />,
            handle: meta({ titleKey: "routes.notFound.title" }),
          },
        ],
      },
    ],
  },
];
