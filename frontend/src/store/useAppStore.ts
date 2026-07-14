import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Theme = 'dark' | 'light';
type ViewMode = 'journey' | 'forge' | 'observatory' | 'archive';

interface AppState {
  theme: Theme;
  viewMode: ViewMode;
  activeMuid: string | null;
  activeRole: string | null;
  
  // Actions
  setTheme: (theme: Theme) => void;
  setViewMode: (mode: ViewMode) => void;
  setSession: (muid: string, role: string) => void;
  clearSession: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      theme: 'dark', // Default to dark for premium feel
      viewMode: 'journey',
      activeMuid: null,
      activeRole: null,

      setTheme: (theme) => set({ theme }),
      setViewMode: (mode) => set({ viewMode: mode }),
      setSession: (muid, role) => set({ activeMuid: muid, activeRole: role }),
      clearSession: () => set({ activeMuid: null, activeRole: null, viewMode: 'journey' }),
    }),
    {
      name: 'muway-storage',
    }
  )
);
