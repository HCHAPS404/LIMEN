import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { I18nextProvider } from "react-i18next";

import { TooltipProvider } from "../../components/primitives/Tooltip";
import i18n from "../../i18n";
import { AuthProvider } from "./AuthProvider";
import { createQueryClient } from "./queryClient";
import { ThemeProvider } from "./ThemeProvider";

export function AppProviders({
  children,
  client,
}: {
  children: ReactNode;
  client?: QueryClient;
}) {
  const [queryClient] = useState(() => client ?? createQueryClient());

  return (
    <I18nextProvider i18n={i18n}>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <TooltipProvider>{children}</TooltipProvider>
          </AuthProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </I18nextProvider>
  );
}
