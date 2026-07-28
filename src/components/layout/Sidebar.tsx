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
  Globe 
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { activeTab, setActiveTab, lang, setLang, theme, toggleTheme } = useStudioStore();

  const navItems: { id: ActiveTab; label: string; icon: React.ReactNode }[] = [
    { id: 'home', label: '首页', icon: <Home className="size-4" /> },
    { id: 'playground', label: '实验场', icon: <FlaskConical className="size-4" /> },
    { id: 'search', label: '检索', icon: <Search className="size-4" /> },
    { id: 'logs', label: '请求日志', icon: <FileText className="size-4" /> },
    { id: 'sessions', label: '会话', icon: <MessageSquare className="size-4" /> },
  ];

  return (
    <aside className="w-64 border-r border-slate-200/80 bg-slate-50/50 flex flex-col justify-between p-4 h-[calc(100vh-3.5rem)] text-sm sticky top-14">
      {/* 顶部主导航菜单 */}
      <div className="space-y-1">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
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

      {/* 底部功能栏：语言/明暗切换 -> 版本号 -> 连接与身份等 */}
      <div className="space-y-3 pt-4 border-t border-slate-200/80">
        {/* 1. 右上角迁移过来的语言与明暗切换控件 */}
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

        {/* 2. 版本号硬性声明 (位于连接与身份上方) */}
        <div className="px-3 py-1.5 rounded-md bg-slate-100 text-slate-500 text-xs font-mono font-medium flex items-center justify-between border border-slate-200/50">
          <span>系统版本</span>
          <span className="bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-bold">v1.1.2</span>
        </div>

        {/* 3. 底部原有候选与身份入口 */}
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
    </aside>
  );
};
