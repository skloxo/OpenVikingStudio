import React from 'react';
import { Menu, X } from 'lucide-react';
import { useStudioStore } from '../../store/useStudioStore';

export const Navbar: React.FC = () => {
  const { isMobileMenuOpen, toggleMobileMenu } = useStudioStore();

  return (
    <header className="h-14 border-b border-slate-200/80 bg-white/80 backdrop-blur-md px-4 md:px-6 flex items-center justify-between shadow-2xs sticky top-0 z-30">
      <div className="flex items-center gap-3">
        {/* 移动端专属汉堡包菜单切换按钮 */}
        <button
          onClick={toggleMobileMenu}
          className="md:hidden flex items-center justify-center p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition"
          aria-label="Toggle Navigation Menu"
        >
          {isMobileMenuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>

        <div className="size-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-base shadow-sm">
          OV
        </div>
        <div>
          <span className="font-semibold text-slate-900 tracking-tight text-base">OpenViking Studio</span>
          <span className="ml-2 text-xs text-slate-400 font-mono">v1.2.38</span>
        </div>
      </div>
    </header>
  );
};
