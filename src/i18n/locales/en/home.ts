export const home = {
  home: {
    peerAgents: {
      title: 'AGENT PEER MEMORY HUB DASHBOARD',
      subtitle: 'viking://user/default/peers/',
      agfsMesh: 'AgFS Peer Memory Mesh',
      messagesCount: 'Messages Deposited',
      statusRunning: 'ACTIVE',
      statusReady: 'IDLE',
      statusStandby: 'STANDBY',
      connectionType: 'Channel',
      realtimeApi: 'Local IPC',
      apiClient: 'Remote API',
      primaryEngine: 'Core Engine',
      synced: 'Synced',
      listening: 'Watching',
      syncing: 'Building',
      skillsMounted: 'Mounted Skills',
      uri: 'Viking URI Node',
      masterMemory: 'master_memory Hub',
      singleSource: 'Viking Single Source of Truth',
      agents: {
        antigravity: 'Antigravity',
        antigravity_v2: 'Antigravity 2.0',
        openclaw: 'OpenClaw',
        tidetrading: 'Tide-Trading',
        hermes: 'Hermes',
        mimo_code: 'MIMO Code',
        developer: 'Developer',
        operator: 'Operator',
        openviking: 'OpenViking',
      },
      roles: {
        antigravity: 'IDE Host',
        antigravity_v2: 'v2.0 Agent',
        openclaw: 'Agent Hub',
        tidetrading: 'Quant Trading',
        hermes: '7x24 Ops Sentinel',
        mimo_code: 'Intelligence Engine',
        developer: 'Core Code Engine',
        operator: 'Container Guardian',
        openviking: 'VK Storage Hub',
      },
    },
    contextCommits: {
      description:
        'Groups resource, skill, session message, and session commit writes into 4-hour buckets. Hover a cell for details.',
      empty: 'No context commits in the last year',
      hourRange: '{{start}}-{{end}}',
      legend: {
        high: 'High',
        intense: 'Intense',
        low: 'Low',
        medium: 'Medium',
        more: 'More',
        none: 'Less',
        title: 'Commit intensity',
      },
      operations: {
        addResource: 'Resource writes',
        addSkill: 'Skill writes',
        sessionAddMessage: 'Session messages',
        sessionCommit: 'Session commits',
      },
      stats: {
        activeDays: 'Active days',
        peakDay: 'Peak day',
        recentDay: 'Recent commit',
      },
      title: 'Context Commit Stats',
      yearlyEmpty: 'No context commits',
      yearlyTotal: '{{count}} context commits',
      tooltip: {
        total: 'Total commits',
      },
    },
    contextData: {
      description:
        'Includes files, skills, and user memories to measure context scale.',
      files: 'Files',
      memories: 'Memories',
      skills: 'Skills',
      title: 'Context Asset Distribution',
    },
    knowledgeBaseOverview: {
      title: 'Knowledge Base Overview & Vector Engine',
      subtitle: 'Overview of business asset nodes and vector distribution',
      memoryAssets: 'Memory Nodes',
      resourceAssets: 'Resource Files',
      skillAssets: 'Skill Nodes',
      totalVectors: 'Total Vector Records',
      activeCollections: 'Active Collection Spaces',
      healthyEngine: 'Vector Engine Healthy',
      vectorEngineTitle: 'VikingDB Vector Engine Space',
      totalAssetsLabel: 'Total Computed Assets:',
      nodeUnit: 'Nodes',
      spacesUnit: 'Collection Spaces',
    },
    systemResourceChart: {
      title: 'Global Token Consumption & Retrieval Trends',
      subtitle: 'Resource allocation overview of models and context retrieval over the past 14 days',
      tokensLabel: 'Tokens Consumed',
      retrievalsLabel: 'Retrieval Requests',
      range14d: 'Last 14 Days',
      range30d: 'Last 30 Days',
      noData: 'No trend data available',
    },
    page: {
      description:
        'Aligned with the product overview: menu entries, context data volume, today tokens, today retrievals, agent access, token trend, and context commit stats.',
      eyebrow: 'OpenViking Studio',
      settings: 'Connection & Settings',
      title: 'Overview',
    },
    requestFailed: 'Request failed',
    todayRetrievals: {
      description:
        'Shows successful semantic retrieval calls for find() and search() today. Resets at midnight.',
      find: 'find',
      search: 'search',
      title: 'Retrievals Today',
    },
    todayTokens: {
      description:
        'Shows real-time token consumption today. Resets at midnight.',
      embeddingInput: 'Embedding input tokens',
      title: 'Tokens Today',
      vlmInput: 'VLM input tokens',
      vlmOutput: 'VLM output tokens',
    },
    tokenTrend: {
      description:
        'Shows daily token usage over the last 14 days, including VLM input, VLM output, and embedding input.',
      empty: 'No token usage in the last 14 days',
      title: 'Total Token Consumption',
    },
    usageDisabled:
      'Usage/Audit is not initialized, so live usage stats are unavailable.',
    usageAccessRequired:
      'Current connection has no admin/root role. Configure an API key with Console Usage/Audit access in Connection & Identity.',
  },
} as const

export default home
