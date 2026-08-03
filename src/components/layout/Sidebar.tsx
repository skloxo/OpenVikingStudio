import React from 'react';
import { useStudioStore } from '../../store/useStudioStore';
import type { ActiveTab } from '../../types';
import { 
  Home, 
  FlaskConical, 
  Search, 
  FileText, 
  MessageSquare, 
  ShieldCheck, 
  KeyRound, 
  Github, 
  BookOpen, 
  Sun, 
  Moon, 
  Globe,
  X
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { 
    activeTab, 
    setActiveTab, 
    lang, 
    setLang, 
    theme, 
    toggleTheme,
    isMobileMenuOpen,
    setIsMobileMenuOpen
  } = useStudioStore();

  const navItems: { id: ActiveTab; label: string; icon: React.ReactNode }[] = [
    { id: 'home', label: '首页', icon: <Home className="size-4" /> },
    { id: 'playground', label: '实验场', icon: <FlaskConical className="size-4" /> },
    { id: 'search', label: '检索', icon: <Search className="size-4" /> },
    { id: 'logs', label: '请求日志', icon: <FileText className="size-4" /> },
    { id: 'sessions', label: '会话', icon: <MessageSquare className="size-4" /> },
  ];

  const SidebarInner = () => (
    <div className="flex flex-col justify-between h-full p-4 text-sm">
      {/* 顶部主导航菜单 */}
      <div className="space-y-1">
        <div className="md:hidden flex items-center justify-between pb-3 mb-2 border-b border-slate-200/80">
          <span className="font-semibold text-slate-800 text-sm">导航菜单</span>
          <button 
            onClick={() => setIsMobileMenuOpen(false)}
            className="p-1 rounded-md text-slate-500 hover:bg-slate-100"
          >
            <X className="size-4" />
          </button>
        </div>

        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => {
                setActiveTab(item.id);
                setIsMobileMenuOpen(false);
              }}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg font-medium transition-all ${
                isActive 
                  ? 'bg-blue-50 text-blue-600 font-semibold shadow-2xs' 
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* 底部功能栏 */}
      <div className="space-y-3 pt-4 border-t border-slate-200/80">
        <div className="flex items-center justify-between px-2 py-1 bg-white rounded-lg border border-slate-200/60 shadow-2xs">
          <button 
            onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')}
            className="flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium text-slate-600 hover:bg-slate-100 transition"
            title="切换语言"
          >
            <Globe className="size-3.5 text-slate-500" />
            <span>{lang === 'zh' ? '中 / EN' : 'EN / 中'}</span>
          </button>
          <button 
            onClick={toggleTheme}
            className="p-1.5 rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition"
            title="切换明暗模式"
          >
            {theme === 'light' ? <Sun className="size-4 text-amber-500" /> : <Moon className="size-4 text-indigo-400" />}
          </button>
        </div>

        <div className="px-3 py-1.5 rounded-md bg-slate-100 text-slate-500 text-xs font-mono font-medium flex items-center justify-between border border-slate-200/50">
          <span>系统版本</span>
          <span className="bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-bold">v1.2.35</span>
        </div>

        <div className="space-y-1 text-xs font-medium text-slate-600">
          <button className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-md hover:bg-slate-100 text-slate-700 transition">
            <ShieldCheck className="size-4 text-slate-500" />
            <span>连接与身份</span>
          </button>
          <button className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-md hover:bg-slate-100 text-slate-700 transition">
            <KeyRound className="size-4 text-slate-500" />
            <span>OAuth 验证</span>
          </button>
          <a 
            href="https://github.com/volcengine/OpenViking" 
            target="_blank" 
            rel="noopener noreferrer"
            className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-md hover:bg-slate-100 text-slate-700 transition"
          >
            <Github className="size-4 text-slate-500" />
            <span>GitHub</span>
          </a>
          <a 
            href="https://github.com/volcengine/OpenViking/blob/main/docs/README.md" 
            target="_blank" 
            rel="noopener noreferrer"
            className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-md hover:bg-slate-100 text-slate-700 transition"
          >
            <BookOpen className="size-4 text-slate-500" />
            <span>文档站</span>
          </a>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* 桌面端固定的侧边栏 */}
      <aside className="hidden md:flex w-64 border-r border-slate-200/80 bg-slate-50/50 flex-col justify-between h-[calc(100vh-3.5rem)] text-sm sticky top-14">
        <SidebarInner />
      </aside>

      {/* 移动端侧滑抽屉遮罩与面板 */}
      {isMobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* 半透明黑色背景 */}
          <div 
            className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity"
            onClick={() => setIsMobileMenuOpen(false)}
          />

          {/* 侧滑抽出内容区 */}
          <div className="relative w-64 max-w-[80vw] bg-white border-r border-slate-200 shadow-xl flex flex-col h-full z-10 animate-in slide-in-from-left duration-200">
            <SidebarInner />
          </div>
        </div>
      )}
    </>
  );
};
