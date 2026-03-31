import { create } from "zustand";
import { persist } from "zustand/middleware";
import { User } from "@/types";
import { api, setAccessToken } from "./api";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  login: (email: string, password: string, totp_code?: string) => Promise<void>;
  logout: () => Promise<void>;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,

      setUser: (user) => set({ user }),

      login: async (email, password, totp_code) => {
        set({ isLoading: true });
        try {
          const res = await api.login(email, password, totp_code);
          const { access_token } = res.data.data;
          setAccessToken(access_token);
          await get().fetchMe();
        } finally {
          set({ isLoading: false });
        }
      },

      logout: async () => {
        try {
          await api.logout();
        } finally {
          setAccessToken(null);
          set({ user: null });
          if (typeof window !== "undefined") window.location.href = "/auth/login";
        }
      },

      fetchMe: async () => {
        try {
          const res = await api.getMe();
          set({ user: res.data.data });
        } catch {
          set({ user: null });
        }
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({ user: state.user }),
    }
  )
);
