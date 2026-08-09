import { create } from "zustand";

/** Ephemeral UI shape only. Server data belongs to TanStack Query. */
type UiState = {
  railExpanded: boolean;
  toggleRail: () => void;
};

export const useUiStore = create<UiState>((set) => ({
  railExpanded: true,
  toggleRail: () => set((state) => ({ railExpanded: !state.railExpanded })),
}));
