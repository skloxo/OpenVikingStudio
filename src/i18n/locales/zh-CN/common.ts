export const common = {
  common: {
    action: {
      cancel: '取消',
      saveConnection: '保存连接',
      showAdvancedIdentityFields: '显示高级身份字段',
    },
    errorBoundary: {
      description:
        '路由渲染过程中出现未处理异常。可以先重试一次；如果问题持续，查看下方错误信息继续排查。',
      reload: '刷新页面',
      retry: '重试',
      title: '页面发生错误',
    },
    language: {
      current: '当前',
      label: '语言',
    },
    theme: {
      toggle: '切换主题',
    },
  },
  appShell: {
    footer: {
      agentIntegrations: 'Agent 接入',
      connection: '连接设置',
      docs: '文档站',
      github: 'GitHub',
      sdkApi: 'SDK 与 API',
      users: '用户管理',
    },
    header: {
      currentUser: {
        account: '账号',
        accountSummary: '账号 · {{account}}',
        loadingUsers: '正在加载用户',
        loadUsersFailed: '用户列表加载失败',
        noUsers: '当前账号暂无用户',
        openMenu: '查看当前用户 {{user}}',
        retry: '重试',
        signedInAs: '当前数据访问身份',
        switchSuccess: '用户切换成功',
        switchAction: '切换用户',
        switchUser: '切换用户',
        unset: '未设置',
        user: '用户',
        userId: '用户 ID',
        userIdPlaceholder: '输入用户 ID',
      },
      defaultTitle: 'OpenViking Studio',
    },
    navigation: {
      home: {
        title: '系统首页',
      },
      crossDeviceVerify: {
        title: 'OAuth 验证',
      },
      operations: {
        title: '运维',
      },
      requestLogs: {
        title: '请求日志',
      },
      monitoring: {
        title: '系统监控',
      },
      skills: {
        title: '技能中心',
      },
      harnessLogs: {
        title: '哈尼斯技能演进审计',
      },
      resources: {
        title: '资源库',
      },
      graph: {
        title: '关系图谱',
      },
      tasks: {
        title: '任务中心',
      },
      retrieval: {
        title: '信息治理',
      },
      sessions: {
        title: '会话中心',
      },
      users: {
        title: '用户管理',
      },
      settings: {
        title: '设置中枢',
      },
      playground: {
        title: '交互沙盘',
      },
    },
    sidebar: {
      groups: {
        operations: '活动',
        resources: '资源',
        settings: '设置',
        workspace: '工作区',
      },
      loadingSessions: '加载中...',
      noSessions: '暂无会话',
      workspaceGroupLabel: 'OpenViking Studio',
      doctorPill: '1933 核心健康',
      doctorPillTooltip: '点击打开系统健康探针与自愈面板',
    },
    doctor: {
      title: 'OpenViking 系统健康探针与自愈中枢',
      description: '实时探测 1933 RPC 服务、AGFS 文件系统挂载、VectorDB 向量引擎与鉴权门禁状态，支持一键物理自愈。',
      statusHealthy: '1933 核心健康',
      statusAbnormal: '连接异常',
      recheck: '重新探测',
      healNow: '一键物理自愈 (Run Doctor)',
      healing: '正在自愈 ({{step}}/3)...',
      healSuccess: '系统自愈完成，所有服务已恢复最优状态',
      probing: '正在探测服务端心跳...',
      lastCheck: '最近探测',
      terminalLogs: '自愈诊断流水线 (Doctor Pipeline)',
    },
  },
  accountSwitcher: {
    create: '新建 Account',
    dialog: {
      accountLabel: 'Account',
      accountPlaceholder: 'team-account',
      adminLabel: '初始 Admin user',
      cancel: '取消',
      description:
        '创建一个新的空间和首个管理员。创建完成后将自动切换到该空间。',
      submit: '创建并切换',
      title: '新建 Account',
    },
    empty: '没有匹配的 Account',
    errors: {
      loadAccounts: '加载 Account 失败',
      noCreatedKey: 'Account 已创建，但服务端没有返回可用于切换的数据凭证。',
      noUsableKey: '该 Account 没有可用于数据访问的明文 User API Key。',
      noUsers: '该 Account 下没有可用用户。',
    },
    loading: '正在加载 Accounts...',
    manualSwitch: {
      description:
        '服务端没有返回 {{account}} 下的明文凭证。请输入该 Account 中任意用户的 User API Key。',
      hint: 'API Key 只用于校验并切换当前数据身份，不会修改或重新生成服务端凭证。',
      keyLabel: 'User API Key',
      keyPlaceholder: '粘贴目标 Account 的 User API Key',
      manageOnly: '仅管理该 Account',
      submit: '验证并切换',
      title: '输入 User API Key',
    },
    memberCount: '{{count}} 个用户',
    searchPlaceholder: '搜索 Account',
    toast: {
      created: '已创建并切换到 {{account}}',
      createdSwitchFailed:
        '{{account}} 已创建，但数据身份切换失败：{{error}}。仍可进入该 Account 管理用户。',
      managementSwitched:
        '管理空间已切换到 {{account}}。访问租户数据前，请先选择或创建 User Key。',
      switched: '已切换到 {{account}}',
    },
    unset: '未选择 Account',
  },
  connection: {
    devMode: {
      description:
        '当前服务会自动提供身份，通常不需要填写 account、user 和 API key。',
      title: '服务端托管身份',
    },
    dialog: {
      title: '连接与身份',
    },
    identitySummary: {
      dev: '服务端隐式身份',
      named: '{{identity}}',
      unset: '未设置身份',
    },
    fields: {
      accountId: {
        label: 'Account',
        placeholder: 'default',
      },
      apiKey: {
        label: 'API Key',
        placeholder: '输入 X-API-Key 或 Bearer token',
      },
      adminApiKey: {
        label: 'Admin API key',
        placeholder: 'Root 或 account-admin key',
      },
      baseUrl: {
        label: '服务地址',
        placeholder: 'http://127.0.0.1:1933',
      },
      credentials: {
        title: '身份与凭证',
      },
      dataApiKey: {
        label: 'User API key',
      },
      userId: {
        label: 'User',
        placeholder: 'default',
      },
    },
  },
  oauth: {
    identityPicker: {
      useCurrent: '以当前身份授权',
      noCurrent:
        '尚未配置身份。请先在“连接与身份”中登录，或在下方临时粘贴一个 API key。',
      useSelect: '授权指定的账号 / 用户',
      selectAccountLabel: '账号',
      selectUserLabel: '用户',
      selectNoKey:
        '该用户没有 API key，请选择其他用户，或在“连接与身份”中重新生成。',
      selectAccountAdminHint: '你只能为本账号下的用户授权。',
      useCustom: '使用其他 API key',
      customKeyLabel: 'API key',
      customKeyPlaceholder: '粘贴一个 API key（不会持久化）',
    },
    consent: {
      title: '授权 {{clientName}}',
      loading: '正在加载授权请求…',
      expired: '此次授权已过期或不再有效，请从 MCP 客户端重新发起。',
      missingPending: '缺少授权 ID，请打开 MCP 客户端给出的链接。',
      requestSummary: '{{clientName}} 请求访问你的 OpenViking 工作区。',
      redirectLabel: '回跳地址',
      scopesLabel: '权限范围',
      scopesNone: '（无）',
      signInRequired:
        '请先在“连接与身份”中登录 OpenViking Studio，或在下方临时粘贴 API key 完成授权。',
      openConnectionSettings: '打开连接与身份',
      authorize: '授权',
      deny: '拒绝',
      useAnotherDevice: '在另一台设备上授权 →',
      waitingRedirect: '已授权——正在回跳到客户端…',
      verifying: '正在验证…',
      denying: '正在拒绝…',
      denied: '已拒绝，可以关闭此页。',
      verifyError: '授权失败：{{message}}',
      noApiKey: '没有可用的 API key。请选择一个身份或粘贴 key。',
    },
    verify: {
      title: '跨设备验证',
      description: '请输入发起 MCP 客户端登录的那台设备上显示的 6 位验证码。',
      codeLabel: '验证码',
      codePlaceholder: '6 位验证码',
      submit: '授权',
      success: '已为 {{clientName}} 授权，可以关闭此页并回到原设备。',
      successUnknownClient: '已授权，可以关闭此页并回到原设备。',
      verifyError: '授权失败：{{message}}',
      noApiKey: '没有可用的 API key。请选择一个身份或粘贴 key。',
      signInRequired:
        '请先在“连接与身份”中登录 OpenViking Studio，或在下方临时粘贴 API key 完成授权。',
    },
  },
} as const

export default common
