import { create } from "zustand";

type UiState = {
  lastVisited: string;
  setLastVisited: (path: string) => void;
};

export const useUiStore = create<UiState>((set) => ({
  lastVisited: "/call",
  setLastVisited: (path) => set({ lastVisited: path }),
}));
