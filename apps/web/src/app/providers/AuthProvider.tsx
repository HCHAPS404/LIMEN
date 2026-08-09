import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, type ReactNode } from "react";

import {
  authKeys,
  deleteAccount,
  fetchAccount,
  login,
  logout,
  register,
  type AccountResponse,
} from "../../api/auth";

export type AuthStatus = "loading" | "authenticated" | "anonymous";

type AuthContextValue = {
  status: AuthStatus;
  account: AccountResponse | null;
  signIn: (input: { email: string; password: string }) => Promise<void>;
  signUp: (input: {
    email: string;
    password: string;
    displayName: string;
  }) => Promise<void>;
  signOut: () => Promise<void>;
  isSigningOut: boolean;
  deleteAccount: () => Promise<void>;
  isDeletingAccount: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  const session = useQuery({
    queryKey: authKeys.me,
    queryFn: ({ signal }) => fetchAccount(signal),
    // A 401 is the expected answer for a visitor, not a failure worth retrying.
    retry: false,
    staleTime: 60_000,
  });

  const signIn = useMutation({
    mutationFn: login,
    onSuccess: (data) => queryClient.setQueryData(authKeys.me, data.account),
  });

  const signUp = useMutation({
    mutationFn: register,
    onSuccess: (data) => queryClient.setQueryData(authKeys.me, data.account),
  });

  const clearSessionCache = () => {
    // Cached clinical data belongs to the account that just left.
    queryClient.setQueryData(authKeys.me, null);
    queryClient.clear();
  };

  const signOut = useMutation({
    mutationFn: logout,
    onSettled: clearSessionCache,
  });

  const removeAccount = useMutation({
    mutationFn: deleteAccount,
    onSettled: clearSessionCache,
  });

  const account = session.data ?? null;
  const status: AuthStatus = session.isPending
    ? "loading"
    : account
      ? "authenticated"
      : "anonymous";

  return (
    <AuthContext.Provider
      value={{
        status,
        account,
        signIn: async (input) => {
          await signIn.mutateAsync(input);
        },
        signUp: async (input) => {
          await signUp.mutateAsync(input);
        },
        signOut: async () => {
          await signOut.mutateAsync();
        },
        isSigningOut: signOut.isPending,
        deleteAccount: async () => {
          await removeAccount.mutateAsync();
        },
        isDeletingAccount: removeAccount.isPending,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
