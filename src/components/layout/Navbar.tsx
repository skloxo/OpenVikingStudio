import React from 'react';

export const Navbar: React.FC = () => {
  return (
    <header className="h-14 border-b border-slate-200/80 bg-white/80 backdrop-blur-md px-6 flex items-center justify-between shadow-2xs sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <div className="size-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-base shadow-sm">
          OV
        </div>
        <div>
          <span className="font-semibold text-slate-900 tracking-tight text-base">OpenViking Studio</span>
          <span className="ml-2 text-xs text-slate-400 font-mono">v0.4.10</span>
        </div>
      </div>
    </header>
  );
};
