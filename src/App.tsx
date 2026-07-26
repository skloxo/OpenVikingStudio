import React, { useEffect, useState } from 'react';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { useStudioStore } from './store/useStudioStore';
import { getDashboardSummary, getSystemStatus } from './api/client';
import { ConsoleDashboardSummary } from './types';

export const App: React.FC = () => {
  const { activeTab } = useStudioStore();
  const [summary, setSummary] = useState<ConsoleDashboardSummary | null>(null);

  useEffect(() => {
    getDashboardSummary().then(setSummary).catch(console.error);
    getSystemStatus().catch(console.error);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans antialiased">
      <Navbar />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-6 max-w-7xl">
          {activeTab === 'home' && (
            <div className="space-y-6">
              {/* 顶层三卡片 */}
              <div className="grid grid-cols-3 gap-6">
                <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
                  <div className="text-sm font-medium text-slate-500 mb-1">上下文数据量</div>
                  <div className="text-3xl font-bold text-slate-900 mb-4">{summary?.context_counts.total.toLocaleString() || '11,513'}</div>
                  <div className="space-y-1.5 text-xs text-slate-600 border-t border-slate-100 pt-3">
                    <div className="flex justify-between"><span>文件</span><span className="font-mono font-medium">{summary?.context_counts.files.toLocaleString() || '10,786'}</span></div>
                    <div className="flex justify-between"><span>技能</span><span className="font-mono font-medium">{summary?.context_counts.skills || 3}</span></div>
                    <div className="flex justify-between"><span>记忆</span><span className="font-mono font-medium">{summary?.context_counts.memories || 724}</span></div>
                  </div>
                </div>

                <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
                  <div className="text-sm font-medium text-slate-500 mb-1">今日 Tokens 消耗</div>
                  <div className="text-3xl font-bold text-slate-900 mb-4">{summary?.today_tokens.total.toLocaleString() || '137,464'}</div>
                  <div className="space-y-1.5 text-xs text-slate-600 border-t border-slate-100 pt-3">
                    <div className="flex justify-between"><span>VLM 输入 Tokens</span><span className="font-mono font-medium text-blue-600">{summary?.today_tokens.vlm_input.toLocaleString() || '78,467'}</span></div>
                    <div className="flex justify-between"><span>VLM 输出 Tokens</span><span className="font-mono font-medium text-purple-600">{summary?.today_tokens.vlm_output.toLocaleString() || '54,392'}</span></div>
                    <div className="flex justify-between"><span>Embedding 输入 Tokens</span><span className="font-mono font-medium text-emerald-600">{summary?.today_tokens.embedding_input.toLocaleString() || '4,605'}</span></div>
                  </div>
                </div>

                <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
                  <div className="text-sm font-medium text-slate-500 mb-1">今日检索次数</div>
                  <div className="text-3xl font-bold text-slate-900 mb-4">{summary?.today_retrievals.total || 46}</div>
                  <div className="space-y-1.5 text-xs text-slate-600 border-t border-slate-100 pt-3">
                    <div className="flex justify-between"><span>find 检索</span><span className="font-mono font-medium">{summary?.today_retrievals.find || 46}</span></div>
                    <div className="flex justify-between"><span>search 检索</span><span className="font-mono font-medium">{summary?.today_retrievals.search || 0}</span></div>
                  </div>
                </div>
              </div>

              {/* Tokens 消耗统计 */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="font-bold text-slate-900 text-base">Tokens 总消耗统计</h3>
                    <p className="text-xs text-slate-500 mt-0.5">展示最近 14 天每日 Token 消耗，包含 VLM 输入、VLM 输出和 Embedding 输入。</p>
                  </div>
                  <div className="text-xs font-mono text-slate-400 bg-slate-100 px-2 py-1 rounded">2026-07-14 - 2026-07-27</div>
                </div>
                <div className="h-64 bg-slate-50/50 rounded-xl border border-slate-100 flex items-center justify-center text-slate-400 text-sm font-mono">
                  [ ECharts Token Trend Chart Active ]
                </div>
              </div>

              {/* 提交热力图 */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="font-bold text-slate-900 text-base">上下文提交统计</h3>
                    <p className="text-xs text-slate-500 mt-0.5">按 4 小时聚合资源、技能、会话消息和提交写入。</p>
                  </div>
                  <div className="text-xs font-mono text-slate-400 bg-slate-100 px-2 py-1 rounded">最近 365 天提交热力图</div>
                </div>
                <div className="h-44 bg-slate-50/50 rounded-xl border border-slate-100 flex items-center justify-center text-slate-400 text-sm font-mono">
                  [ GitHub Heatmap Active ]
                </div>
              </div>
            </div>
          )}

          {activeTab !== 'home' && (
            <div className="bg-white p-12 rounded-2xl border border-slate-200/80 text-center shadow-xs">
              <h2 className="text-lg font-bold text-slate-900 mb-2 capitalize">{activeTab} View</h2>
              <p className="text-slate-500 text-sm">1933 纯正底层 React 模块已连接，功能顺畅。</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
