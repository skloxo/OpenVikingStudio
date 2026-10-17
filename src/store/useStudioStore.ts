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
  isMobileMenuOpen: boolean;
  setIsMobileMenuOpen: (open: boolean) => void;
  toggleMobileMenu: () => void;
}

export const useStudioStore = create<StudioState>((set) => ({
  activeTab: 'home',
  setActiveTab: (tab: ActiveTab) => set({ activeTab: tab, isMobileMenuOpen: false }),
  lang: 'zh',
  setLang: (lang: 'zh' | 'en') => set({ lang }),
  theme: 'light',
  toggleTheme: () => set((state: StudioState) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
  systemStatus: null,
  setSystemStatus: (systemStatus: SystemStatus) => set({ systemStatus }),
  isMobileMenuOpen: false,
  setIsMobileMenuOpen: (isMobileMenuOpen: boolean) => set({ isMobileMenuOpen }),
  toggleMobileMenu: () => set((state: StudioState) => ({ isMobileMenuOpen: !state.isMobileMenuOpen })),
}));
