import { create } from 'zustand';
import type { ActiveTab, SystemStatus } from '../types';

interface StudioState {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  lang: 'zh' | 'en';
  setLang: (lang: 'zh' | 'en') => void;
  theme: 'light' | 'dark';
  toggleTheme: () => void;
  systemStatus: SystemStatus | null;
  setSystemStatus: (status: SystemStatus) => void;
}

export const useStudioStore = create<StudioState>((set) => ({
  activeTab: 'home',
  setActiveTab: (tab: ActiveTab) => set({ activeTab: tab }),
  lang: 'zh',
  setLang: (lang: 'zh' | 'en') => set({ lang }),
  theme: 'light',
  toggleTheme: () => set((state: StudioState) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
  systemStatus: null,
  setSystemStatus: (systemStatus: SystemStatus) => set({ systemStatus }),
}));
