import { useQuery } from "@tanstack/react-query";

import { getTrace, traceKeys } from "../../api/traces";

export function useTrace(callId: string | undefined) {
  return useQuery({
    queryKey: traceKeys.detail(callId ?? "none"),
    queryFn: ({ signal }) => getTrace(callId as string, signal),
    enabled: Boolean(callId),
  });
}
