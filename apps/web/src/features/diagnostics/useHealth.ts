import { useQuery } from "@tanstack/react-query";

import { fetchHealth, healthKeys } from "../../api/health";
import type { ConnectionStatus } from "../../components/feedback/ConnectionState";

export function useHealth() {
  return useQuery({
    queryKey: healthKeys.root,
    queryFn: ({ signal }) => fetchHealth(signal),
    refetchInterval: 30_000,
  });
}

export function healthConnectionStatus(query: {
  isPending: boolean;
  isError: boolean;
  isSuccess: boolean;
}): ConnectionStatus {
  if (query.isPending) return "connecting";
  if (query.isError) return "disconnected";
  if (query.isSuccess) return "connected";
  return "unavailable";
}
