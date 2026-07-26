import { create } from 'zustand';
import { ActiveTab, SystemStatus } from '../types';

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
  setActiveTab: (tab) => set({ activeTab: tab }),
  lang: 'zh',
  setLang: (lang) => set({ lang }),
  theme: 'light',
  toggleTheme: () => set((state) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
  systemStatus: null,
  setSystemStatus: (systemStatus) => set({ systemStatus }),
}));
