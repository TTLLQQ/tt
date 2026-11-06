import { create } from "zustand";

export const useAuth = create((set) => ({
  token: localStorage.getItem("tt_access_token") || "",
  user: null,
  setAuth: (token, user) => {
    localStorage.setItem("tt_access_token", token);
    set({ token, user });
  },
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.removeItem("tt_access_token");
    set({ token: "", user: null });
  }
}));
