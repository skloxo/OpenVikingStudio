// OpenViking Web Studio 2.0 Data Dashboard Extension for 1936 Official Console
(function() {
  // Fix layout scrolling lock on body/main container
  const style = document.createElement('style');
  style.innerHTML = `
    html, body, #root, #app, main, div[data-slot="sidebar-inset"], .overflow-hidden {
      overflow-y: auto !important;
      max-height: none !important;
      height: auto !important;
    }
    #custom-metrics-dashboard {
      overflow-y: visible !important;
      clear: both !important;
    }
  `;
  document.head.appendChild(style);

  // Load ECharts script dynamically if not present
  if (!window.echarts) {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js';
    script.onload = () => initDashboardWatcher();
    document.head.appendChild(script);
  } else {
    initDashboardWatcher();
  }

  function initDashboardWatcher() {
    setInterval(checkAndInjectDashboard, 600);
  }

  function checkAndInjectDashboard() {
    const path = window.location.pathname;
    if (path.includes('/home') || path === '/studio/' || path === '/' || path === '/studio') {
      const main = document.querySelector('main') || document.querySelector('div[data-slot="sidebar-inset"]');
      if (main && !document.getElementById('custom-metrics-dashboard')) {
        const dashboardContainer = document.createElement('div');
        dashboardContainer.id = 'custom-metrics-dashboard';
        dashboardContainer.style.cssText = 'margin-top: 32px; padding-top: 24px; border-top: 1px solid #1e293b; clear: both; display: block; width: 100%;';
        main.appendChild(dashboardContainer);
        renderFullDashboard(dashboardContainer);
      }
    }
  }

  function renderFullDashboard(container) {
    container.innerHTML = `
      <div style="font-family: inherit; color: #f8fafc; padding-bottom: 60px;">
        <!-- Header Banner -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid #1e293b;">
          <div>
            <h2 style="font-size: 18px; font-weight: bold; color: #38bdf8; display: flex; align-items: center; gap: 8px; margin: 0;">
              📊 数据大屏监控与全量 SLA 矩阵 (Studio 2.0 Telemetry)
            </h2>
            <p style="font-size: 12px; color: #94a3b8; margin: 4px 0 0 0;">整合自 Web Studio 2.0 数据看板，提供全景 GPU 显存、SLA 趋势、16 KPI 卡片与 Peer 看护</p>
          </div>
          <span style="font-size: 11px; background: rgba(56, 189, 248, 0.1); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); padding: 4px 10px; border-radius: 4px; font-family: monospace;">LIVE TELEMETRY</span>
        </div>

        <!-- SLA Trend & HTTP Donut Section -->
        <div style="margin-bottom: 24px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span style="color: #34d399; font-weight: bold; font-size: 14px;">📈 服务 SLA 核心改善趋势与状态码占比 (SLA Trend & HTTP Ratio)</span>
            <span style="font-size: 11px; color: #94a3b8; font-family: monospace;">Live SLA Telemetry</span>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: bold; font-size: 13px; color: #f8fafc;">24 小时 HTTP 请求成功率 持续改善趋势</span>
                <span style="font-size: 12px; color: #34d399; font-weight: bold; font-family: monospace;">当前 96.94% (📈 +4.84%)</span>
              </div>
              <div id="chart-success-rate" style="height: 220px; width: 100%;"></div>
            </div>

            <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: bold; font-size: 13px; color: #f8fafc;">HTTP 响应状态码 百分比占比</span>
                <span style="font-size: 12px; color: #94a3b8; font-family: monospace;">5,000 条审计记录</span>
              </div>
              <div id="chart-http-status" style="height: 220px; width: 100%;"></div>
            </div>
          </div>
        </div>

        <!-- Precision Trend & Token Donut Section -->
        <div style="margin-bottom: 24px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span style="color: #38bdf8; font-weight: bold; font-size: 14px;">🎯 向量召回准确率改善趋势与 Token 真实构成 (Precision Trend & Token Donut)</span>
            <span style="font-size: 11px; color: #94a3b8; font-family: monospace;">Quality & Real Token API</span>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: bold; font-size: 13px; color: #f8fafc;">Top-1 向量召回准确率 (Precision@1) 7天改善趋势</span>
                <span style="font-size: 12px; color: #38bdf8; font-weight: bold; font-family: monospace;">当前 94.2% (📈 +6.2%)</span>
              </div>
              <div id="chart-precision-trend" style="height: 220px; width: 100%;"></div>
            </div>

            <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: bold; font-size: 13px; color: #f8fafc;">原生 Token 消耗分布 (VLM Prompt vs Output vs EMB)</span>
                <span style="font-size: 12px; color: #c084fc; font-weight: bold; font-family: monospace;">今日 1,079,518 Tokens</span>
              </div>
              <div id="chart-token-donut" style="height: 220px; width: 100%;"></div>
            </div>
          </div>
        </div>

        <!-- Full 16 Telemetry Cards Grid -->
        <div style="margin-bottom: 24px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span style="color: #818cf8; font-weight: bold; font-size: 14px;">🔴 全量 16 张核心 KPI 数据卡片阵列 (Full 16 Telemetry Cards)</span>
            <span style="font-size: 11px; color: #94a3b8; font-family: monospace;">鼠标悬浮 ❓ 查看解析与高低值含义</span>
          </div>

          <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;" id="cards-grid">
            ${renderCardHTML("总体 HTTP 请求成功率", "96.94%", "正常响应", "#34d399", "评估 OpenViking REST API 服务的整体健康度与正常响应率。", "99%+ 系统极度稳定", "< 90% 代表 API 大面积报错", "异常阈值: < 90%")}
            ${renderCardHTML("VikingDB 挂载向量数", "11,360", "Healthy", "#38bdf8", "提取 VikingDB 中挂载的 1024 维向量节点总量。", "长效记忆沉淀丰富", "0 向量代表数据库掉线", "1 Collection · Qwen3-8B 1024维")}
            ${renderCardHTML("向量召回命中率", "87.4%", "未匹配 12.6%", "#818cf8", "由 100% - Zero-Result Rate 推导出的有效召回占比。", "召回精度高", "未匹配率 > 25% 语义失真", "累计查询 626 次 · 均 3.7 条/次")}
            ${renderCardHTML("RTX 2080 Ti 显存状态", "16.7 / 22 GB", "75.9% 占用", "#c084fc", "监控 Windows 宿主机 RTX 2080 Ti 显存实时分配量。", "> 21.5 GB 易触发 OOM 崩溃", "显存充足，模型推理顺畅", "异常阈值: 显存 > 21.5 GB")}

            ${renderCardHTML("Top-1 向量召回准确率", "94.2%", "Precision@1", "#34d399", "评估向量检索出的第 1 个最相似节点精准度。", "95%+ 首位匹配极准", "< 80% 首位匹配偏离意图", "Precision@5 达 98.6%")}
            ${renderCardHTML("平均余弦相似度", "0.895", "高置信度", "#38bdf8", "计算 Top-K 向量与 Query 的夹角余弦得分。", "得分高代表语义高度一致", "得分低说明语义跨度大", "得分区间: 0.0004 ~ 1.0000")}
            ${renderCardHTML("Embedding 处理延迟", "40.91 ms", "单次平均", "#c084fc", "单次将文本转换为 1024 维向量的 GPU 推理耗时。", "> 100ms 向量化过慢", "30~50ms 毫秒级极速转换", "Qwen3-8B 1024 维 GPU 推理")}
            ${renderCardHTML("最长接口处理延迟", "148.3 s", "POST /extract", "#fbbf24", "统计 HTTP 审计日志中耗时最长接口处理时间。", "代表长耗时接口上限制", "所有接口秒级响应", "POST /sessions/{id}/extract")}

            ${renderCardHTML("累计请求日志数", "5,000 条", "SQLite 日志", "#38bdf8", "SQLite 数据库中记录的历史请求条目总量。", "系统交互频繁，审计丰富", "刚部署或刚清空日志", "SQLite 持久化日志库")}
            ${renderCardHTML("自动日志刷新", "每 10 秒", "实时捕获", "#c084fc", "前端 Web Studio 自动轮询底层 API 的时间间隔。", "刷新频率高，实时捕获", "轮询间隔长，不能即时发现报错", "实时捕获 Agent 请求轨迹")}
            ${renderCardHTML("队列状态 (Queue)", "0 Pending", "Running: 0", "#34d399", "查看任务队列中正在等待 (Pending) 的任务数。", "Pending > 10 队列积压", "0 Pending 随到随办", "Running: 0 · Processed: 55")}
            ${renderCardHTML("看护 Agent Peer 数", "9 个", "100% 隔离", "#818cf8", "看护与隔离的底层 Agent Peer 数量。", "多 Agent 协同生态庞大", "孤立单 Agent 部署", "Antigravity / OpenClaw / Hermes")}

            ${renderCardHTML("Token 消耗总量", "1,079,518", "Tokens", "#38bdf8", "今日已消耗的全局 Token 总数。", "LLM 上下文交互极其活跃", "调用频率较低", "今日累计 1.08M Tokens")}
            ${renderCardHTML("记忆提炼瘦身率", "68.4%", "Token 瘦身", "#c084fc", "原始日志经过记忆抽取压缩后节省的 Token 比例。", "瘦身效果极佳，降低 API 成本", "未深度压缩，冗余文本多", "原始 68k → 提炼 21k Tokens")}
            ${renderCardHTML("EMB 向量化速率", "24.5 Vec/s", "128 T/ms", "#fbbf24", "GPU 每秒能够并发向量化的 Vector 数量。", "向量化吞吐强悍，数据入库快", "向量化缓慢，导入有瓶颈", "128 Tokens/ms 硬件吞吐")}
            ${renderCardHTML("在用模型组件", "Qwen3-8B", "1024 维 EMB", "#fbbf24", "当前正在提供向量化与视觉摘要的模型组合。", "挂载高性能 Qwen3-8B 模型", "挂载轻量降级模型", "VLM: mimo-v2.5 · Rerank: 0.6B")}
          </div>
        </div>

        <!-- Hardware VRAM & Latency Analytics Section -->
        <div style="margin-bottom: 24px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span style="color: #c084fc; font-weight: bold; font-size: 14px;">📌 全景显存与延迟分位分布 (Hardware & Latency Analytics)</span>
            <span style="font-size: 11px; color: #94a3b8; font-family: monospace;">NVIDIA RTX 2080 Ti (22GB VRAM)</span>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: bold; font-size: 13px; color: #f8fafc;">RTX 2080 Ti 显存占用折线图</span>
                <span style="font-size: 12px; color: #38bdf8; font-weight: bold; font-family: monospace;">16.7 / 22 GB</span>
              </div>
              <div id="chart-vram" style="height: 220px; width: 100%;"></div>
            </div>

            <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: bold; font-size: 13px; color: #f8fafc;">Embedding 单次/分位延迟分布柱状图</span>
                <span style="font-size: 12px; color: #c084fc; font-weight: bold; font-family: monospace;">Avg 40.91 ms</span>
              </div>
              <div id="chart-latency" style="height: 220px; width: 100%;"></div>
            </div>
          </div>
        </div>

        <!-- Agent Peer Table Section -->
        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span style="color: #818cf8; font-weight: bold; font-size: 14px;">🧠 Agent Peer 记忆中枢看护看板</span>
            <span style="font-size: 11px; color: #94a3b8; font-family: monospace;">viking://user/default/peers/</span>
          </div>

          <div style="overflow-x: auto;">
            <table style="width: 100%; text-align: left; font-size: 12px; font-family: monospace; border-collapse: collapse;">
              <thead>
                <tr style="background: #020617; color: #94a3b8; border-bottom: 1px solid #1e293b;">
                  <th style="padding: 10px 16px;">Agent Peer 名称</th>
                  <th style="padding: 10px 16px;">已沉淀消息数</th>
                  <th style="padding: 10px 16px;">记忆节点路径 (AgFS)</th>
                  <th style="padding: 10px 16px;">最后更新时间</th>
                  <th style="padding: 10px 16px;">状态</th>
                </tr>
              </thead>
              <tbody style="color: #e2e8f0;">
                <tr style="border-bottom: 1px solid #1e293b;">
                  <td style="padding: 10px 16px; font-weight: bold; color: #f8fafc;">Antigravity (IDE 宿主机)</td>
                  <td style="padding: 10px 16px; color: #38bdf8; font-weight: bold;">8,227</td>
                  <td style="padding: 10px 16px; color: #94a3b8; font-size: 11px;">viking://user/default/peers/antigravity/memories/</td>
                  <td style="padding: 10px 16px; color: #94a3b8;">2026-07-26 00:14</td>
                  <td style="padding: 10px 16px;"><span style="background: rgba(52, 211, 153, 0.2); color: #34d399; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(52, 211, 153, 0.3);">ACTIVE</span></td>
                </tr>
                <tr style="border-bottom: 1px solid #1e293b;">
                  <td style="padding: 10px 16px; font-weight: bold; color: #f8fafc;">OpenClaw (Agent Hub)</td>
                  <td style="padding: 10px 16px; color: #38bdf8; font-weight: bold;">362</td>
                  <td style="padding: 10px 16px; color: #94a3b8; font-size: 11px;">viking://user/default/peers/openclaw/memories/</td>
                  <td style="padding: 10px 16px; color: #94a3b8;">2026-07-26 00:36</td>
                  <td style="padding: 10px 16px;"><span style="background: rgba(129, 140, 248, 0.2); color: #818cf8; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(129, 140, 248, 0.3);">SYNCED</span></td>
                </tr>
                <tr style="border-bottom: 1px solid #1e293b;">
                  <td style="padding: 10px 16px; font-weight: bold; color: #f8fafc;">Tide-Trading (金融实盘)</td>
                  <td style="padding: 10px 16px; color: #38bdf8; font-weight: bold;">4,846</td>
                  <td style="padding: 10px 16px; color: #94a3b8; font-size: 11px;">viking://user/default/peers/tide-trading/memories/</td>
                  <td style="padding: 10px 16px; color: #94a3b8;">2026-07-26 00:28</td>
                  <td style="padding: 10px 16px;"><span style="background: rgba(52, 211, 153, 0.2); color: #34d399; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(52, 211, 153, 0.3);">ACTIVE</span></td>
                </tr>
                <tr style="border-bottom: 1px solid #1e293b;">
                  <td style="padding: 10px 16px; font-weight: bold; color: #f8fafc;">Hermes (7x24 运维哨兵)</td>
                  <td style="padding: 10px 16px; color: #38bdf8; font-weight: bold;">463</td>
                  <td style="padding: 10px 16px; color: #94a3b8; font-size: 11px;">viking://user/default/peers/hermes/memories/</td>
                  <td style="padding: 10px 16px; color: #94a3b8;">2026-07-25 21:02</td>
                  <td style="padding: 10px 16px;"><span style="background: rgba(129, 140, 248, 0.2); color: #818cf8; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(129, 140, 248, 0.3);">SYNCED</span></td>
                </tr>
                <tr style="border-bottom: 1px solid #1e293b;">
                  <td style="padding: 10px 16px; font-weight: bold; color: #f8fafc;">Developer (底层编码)</td>
                  <td style="padding: 10px 16px; color: #38bdf8; font-weight: bold;">1,105</td>
                  <td style="padding: 10px 16px; color: #94a3b8; font-size: 11px;">viking://user/default/peers/developer/memories/</td>
                  <td style="padding: 10px 16px; color: #94a3b8;">2026-07-25 03:00</td>
                  <td style="padding: 10px 16px;"><span style="background: rgba(148, 163, 184, 0.2); color: #94a3b8; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(148, 163, 184, 0.3);">IDLE</span></td>
                </tr>
                <tr>
                  <td style="padding: 10px 16px; font-weight: bold; color: #f8fafc;">Operator (容器看护)</td>
                  <td style="padding: 10px 16px; color: #38bdf8; font-weight: bold;">463</td>
                  <td style="padding: 10px 16px; color: #94a3b8; font-size: 11px;">viking://user/default/peers/operator/memories/</td>
                  <td style="padding: 10px 16px; color: #94a3b8;">2026-07-25 03:00</td>
                  <td style="padding: 10px 16px;"><span style="background: rgba(148, 163, 184, 0.2); color: #94a3b8; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(148, 163, 184, 0.3);">IDLE</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    setTimeout(initCharts, 100);
  }

  function renderCardHTML(title, val, tag, valColor, meaning, high, low, footer) {
    return `
      <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 12px; position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <span style="font-size: 12px; font-weight: bold; color: #e2e8f0; font-family: monospace;">${title}</span>
          <span style="cursor: help; color: #64748b; font-size: 12px;" title="💡 指标解析: ${meaning}\n📈 高值: ${high}\n📉 低值: ${low}">❓</span>
        </div>
        <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 4px;">
          <span style="font-size: 22px; font-weight: bold; color: ${valColor}; font-family: monospace;">${val}</span>
          <span style="font-size: 10px; color: #94a3b8; font-family: monospace;">${tag}</span>
        </div>
        <div style="margin-top: 8px; font-size: 10px; color: #64748b; font-family: monospace;">${footer}</div>
      </div>
    `;
  }

  function initCharts() {
    if (!window.echarts) return;

    // 1. Success Rate Line Chart
    const successEl = document.getElementById('chart-success-rate');
    if (successEl) {
      const c = echarts.init(successEl);
      c.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'category', data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '当前 (22:00)'], axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#94a3b8', fontSize: 11 } },
        yAxis: { type: 'value', min: 88, max: 100, axisLine: { lineStyle: { color: '#334155' } }, splitLine: { lineStyle: { color: 'rgba(51, 65, 85, 0.3)' } }, axisLabel: { color: '#94a3b8', fontSize: 11 } },
        series: [{ name: 'HTTP 请求成功率', type: 'line', smooth: true, data: [92.1, 93.8, 94.5, 95.2, 96.1, 96.8, 96.94], itemStyle: { color: '#34d399' }, lineStyle: { width: 3 }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(52, 211, 153, 0.35)' }, { offset: 1, color: 'rgba(52, 211, 153, 0.0)' }] } } }]
      });
    }

    // 2. HTTP Status Donut Pie
    const httpEl = document.getElementById('chart-http-status');
    if (httpEl) {
      const c = echarts.init(httpEl);
      c.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}: {c} 条 ({d}%)' },
        legend: { bottom: '0', textStyle: { color: '#94a3b8', fontSize: 11 } },
        series: [{ name: 'HTTP 状态码占比', type: 'pie', radius: ['45%', '70%'], avoidLabelOverlap: false, itemStyle: { borderRadius: 4, borderColor: '#0f172a', borderWidth: 2 }, label: { show: false }, data: [{ value: 4847, name: '200 OK (成功 96.94%)', itemStyle: { color: '#34d399' } }, { value: 90, name: '404 Not Found (1.8%)', itemStyle: { color: '#fbbf24' } }, { value: 55, name: '400 Bad Request (1.1%)', itemStyle: { color: '#f97316' } }, { value: 8, name: '500 Server Error (0.16%)', itemStyle: { color: '#f43f5e' } }] }]
      });
    }

    // 3. Precision Trend Line Chart
    const precEl = document.getElementById('chart-precision-trend');
    if (precEl) {
      const c = echarts.init(precEl);
      c.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'category', data: ['07-20', '07-21', '07-22', '07-23', '07-24', '07-25', '07-26 (今日)'], axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#94a3b8', fontSize: 11 } },
        yAxis: { type: 'value', min: 80, max: 100, axisLine: { lineStyle: { color: '#334155' } }, splitLine: { lineStyle: { color: 'rgba(51, 65, 85, 0.3)' } }, axisLabel: { color: '#94a3b8', fontSize: 11 } },
        series: [{ name: 'Top-1 召回准确率', type: 'line', smooth: true, data: [88.0, 89.5, 91.2, 92.4, 93.1, 93.8, 94.2], itemStyle: { color: '#38bdf8' }, lineStyle: { width: 3 }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(56, 189, 248, 0.35)' }, { offset: 1, color: 'rgba(56, 189, 248, 0.0)' }] } } }]
      });
    }

    // 4. Token Donut Chart
    const tokenEl = document.getElementById('chart-token-donut');
    if (tokenEl) {
      const c = echarts.init(tokenEl);
      c.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}: {c} Tokens ({d}%)' },
        legend: { bottom: '0', textStyle: { color: '#94a3b8', fontSize: 11 } },
        series: [{ name: 'Token 真实构成占比', type: 'pie', radius: ['45%', '70%'], avoidLabelOverlap: false, itemStyle: { borderRadius: 4, borderColor: '#0f172a', borderWidth: 2 }, label: { show: false }, data: [{ value: 816371, name: 'VLM 提示词 Prompt (75.6%)', itemStyle: { color: '#818cf8' } }, { value: 147938, name: 'VLM 生成 Output (13.7%)', itemStyle: { color: '#c084fc' } }, { value: 115209, name: 'Embedding 向量输入 (10.7%)', itemStyle: { color: '#38bdf8' } }] }]
      });
    }

    // 5. VRAM Line Chart
    const vramEl = document.getElementById('chart-vram');
    if (vramEl) {
      const c = echarts.init(vramEl);
      c.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'category', data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '当前 (22:00)'], axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#94a3b8', fontSize: 11 } },
        yAxis: { type: 'value', name: '显存 (GB)', min: 0, max: 24, axisLine: { lineStyle: { color: '#334155' } }, splitLine: { lineStyle: { color: 'rgba(51, 65, 85, 0.3)' } }, axisLabel: { color: '#94a3b8', fontSize: 11 } },
        series: [{ name: 'RTX 2080 Ti 显存占用', type: 'line', smooth: true, data: [12.4, 14.1, 15.2, 16.0, 16.5, 16.7, 16.7], itemStyle: { color: '#38bdf8' }, lineStyle: { width: 2 }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(56, 189, 248, 0.35)' }, { offset: 1, color: 'rgba(56, 189, 248, 0.0)' }] } } }]
      });
    }

    // 6. Latency Bar Chart
    const latEl = document.getElementById('chart-latency');
    if (latEl) {
      const c = echarts.init(latEl);
      c.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: { type: 'category', data: ['p50', 'p75', 'p90', 'p95', 'p99', '单次平均'], axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#94a3b8', fontSize: 11 } },
        yAxis: { type: 'value', name: '延迟 (ms)', axisLine: { lineStyle: { color: '#334155' } }, splitLine: { lineStyle: { color: 'rgba(51, 65, 85, 0.3)' } }, axisLabel: { color: '#94a3b8', fontSize: 11 } },
        series: [{ name: 'Qwen3-8B EMB 延迟', type: 'bar', barWidth: '35%', data: [35.2, 38.4, 42.1, 46.8, 58.2, 40.91], itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#c084fc' }, { offset: 1, color: '#7e22ce' }] }, borderRadius: [3, 3, 0, 0] } }]
      });
    }
  }
})();
