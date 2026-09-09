export const settings = {
  settings: {
    hub: {
      title: '全局设置与数据管理中枢',
      description: '统一管理通信密钥、模型与向量拓扑、敏感脱敏安全规则及 OVPack 数据备份还原。',
      tabs: {
        general: '基础与服务配置',
        privacy: '隐私与安全脱敏',
        dataOps: '知识包迁移与备份 (OVPack)',
      },
      models: {
        title: '模型与向量端点拓扑',
        description: '实时呈现底层驱动的 VLM 多模态大模型、Embedding 向量引擎与 Rerank 重排模型',
        activeGroup: '已配置模型',
        vlm: 'VLM 多模态大模型',
        embedding: 'Embedding 向量模型',
        rerank: 'Rerank 语义重排',
        compressor: '端侧上下文压缩器 (Compressor)',
        dimension: '向量维度',
        provider: '提供方',
        status: '端点状态',
        healthy: '已就绪',
        noModels: '未检测到模型端点配置，正在使用默认规则',
        calls: '调用',
        tokens: 'Token',
        lastUpdated: '最后活跃',
        noActiveModel: '无活跃模型数据',
      },
      workspace: {
        title: '工作区与存储配置',
        description: 'VikingFS 底层文件系统存储配置与默认写入目标',
        rootUri: '根文件系统路径',
        defaultResourceTarget: '默认资源写入目标',
        defaultSkillTarget: '默认技能写入目标',
        storageEngine: '底层存储引擎',
        vikingfsDesc: 'AGFS 分层存储与原子快照防护机制已开启',
      },
      privacy: {
        title: '隐私与安全脱敏中枢',
        description: '全生命周期敏感数据过滤、PII 打码防护与自定义规则治理',
        categories: '脱敏规则分类',
        toggleMask: '全局敏感凭据打码',
        toggleMaskDesc: '在请求与日志输出中自动对 API Key、Token 实施掩码防护',
        piiMask: 'PII 个人隐私打码',
        piiMaskDesc: '自动识别邮箱、手机号、IP 地址并执行局部星号打码',
        activeRules: '已生效规则数',
        playgroundTitle: '实时脱敏沙盒演练 (Playground)',
        playgroundDesc: '输入含敏感字符的样本，实时检验脱敏引擎过滤后的效果',
        inputLabel: '测试样本输入',
        inputPlaceholder: '输入测试文本，如: Authorization: Bearer sk-99887766aabbccdd, 联络: fsk@8.129.0.26',
        previewBtn: '执行脱敏预览',
        previewOutput: '脱敏过滤结果',
        rulesTableTitle: '敏感词匹配策略',
        ruleName: '规则类别',
        rulePattern: '匹配模式 / 字段',
        ruleAction: '处置策略',
        actionMask: '哈希掩码打码',
        actionRedact: '物理截断剔除',
      },
      dataOps: {
        title: '知识大脑备份与数据迁移 (OVPack)',
        description: '基于标准 .ovpack 容器的一键全量快照、局部资源导出、知识包迁移与灾备恢复',
        exportTitle: '资源包打包导出 (Export)',
        exportDesc: '将指定 Viking 路径及其子树完整打包为标准 .ovpack 归档容器',
        targetUriLabel: '导出目标 Viking URI',
        targetUriPlaceholder: 'viking://resources/ 或 viking://',
        quickScopes: '常用路径:',
        includeVectors: '包含向量快照 (Include Vectors)',
        includeVectorsHint: '一并打包向量索引数据以加速迁移后的语义召回，包体积会相应增大',
        exportBtn: '导出 .ovpack',
        exporting: '正在打包导出...',
        backupTitle: '全量系统快照备份 (Backup)',
        backupDesc: '全量备份全域公开作用域与全部系统状态，生成灾备快照',
        backupBtn: '立即全量备份',
        backingUp: '正在生成系统全量快照...',
        importTitle: '知识包导入与快照还原 (Import & Restore)',
        importDesc: '上传 .ovpack 归档文件，将其解压合并至指定路径，或执行全量灾难恢复',
        selectPackLabel: '选择 .ovpack 归档文件',
        selectPackBtn: '选择归档文件',
        parentUriLabel: '导入挂载父路径 (Parent URI)',
        conflictPolicy: '冲突消解策略',
        conflictFail: '冲突时报错 (Fail)',
        conflictOverwrite: '覆盖已有数据 (Overwrite)',
        conflictSkip: '跳过已有项 (Skip)',
        vectorMode: '向量处理模式',
        vectorAuto: '自动侦测 (Auto)',
        vectorRecompute: '重新计算向量 (Recompute)',
        vectorRequire: '强制校验已有向量 (Require)',
        importBtn: '导入知识包 (Import Pack)',
        importing: '正在上传并导入...',
        restoreBtn: '全量系统快照还原 (Restore)',
        restoring: '正在还原快照...',
        restoreWarning: '警告：全量还原操作将覆盖当前系统数据，请务必提前做好快照备份！',
        restoreConfirm: '确定执行全量系统还原吗？该操作不可撤销。',
        successExport: '已成功触发导出下载！',
        successBackup: '已成功触发全量备份下载！',
        successImport: '已成功导入知识包至 {{uri}}！',
        successRestore: '系统快照还原完成！',
      },
    },
    actions: {
      addAccount: '新增 account',
      addUser: '新增 user',
      cancel: '取消',
      changeRole: '修改 {{user}} 的角色',
      confirmRemoveUser: '删除用户',
      confirmRoleChange: '确认修改',
      copy: '复制',
      currentIdentity: '当前身份',
      refresh: '刷新',
      regenerate: '重新生成',
      removeUser: '删除 {{user}}',
      save: '保存',
      switchIdentity: '切换身份',
      use: '使用',
    },
    connection: {
      accountListLimited:
        '当前 key 不能列出所有 account；如果它有 account-admin 权限，仍可管理选中的 account。',
      adminError: '校验 Root API Key 失败：{{message}}',
      description:
        '租户数据 API 使用 User API Key；控制 API 可单独使用 Root 或 account-admin key。',
      devMode: '当前为开发模式 — 身份自动确定，无需 API key。',
      keyGuide: {
        control: {
          primary:
            '当前 User API Key 已可用于 Playground 和数据访问，普通用户无需配置控制凭证。',
          secondary:
            '如需切换 Account 或管理用户，请向部署管理员索取 Root Key，或向当前 Account 管理员索取 Admin Key。Root Key 位于服务端 ov.conf 的 server.root_api_key。',
          title: '需要管理 Account 或用户？',
        },
        data: {
          primary:
            'Root/Admin API Key 主要用于管理操作，Playground 和租户数据访问需要绑定用户身份的 User API Key。',
          secondary:
            '请在「用户管理」中选择、创建用户或重新生成 User Key，然后将它用作 User API Key。',
          title: '还缺少 User API Key',
        },
        empty: {
          primary: '普通用户：请向当前 Account 管理员索取 User API Key。',
          secondary:
            '部署管理员：Root API Key 位于服务端 ov.conf 的 server.root_api_key；填入后可在「用户管理」中创建或重新生成 User Key。',
          title: '还没有 OpenViking API Key？',
        },
        learnMore: '查看 API Key 获取方式',
        trusted: {
          primary:
            '当前 Trusted 服务启用了 Root Key 校验，浏览器需要配置同一 Root API Key 才能访问管理和租户数据接口。',
          secondary:
            '请向部署管理员索取 Root Key；它位于服务端 ov.conf 的 server.root_api_key。Trusted 模式的数据身份由 Account/User 断言确定，不需要 User API Key。',
          title: 'Trusted 服务需要 Root API Key',
        },
      },
      rootHint: '用于列出 account / user，以及生成或轮换 key。',
      title: '连接设置',
      recheck: '重新检测',
      rechecking: '正在重新检测服务连通性与探针...',
      unsupportedAuthMode: {
        description:
          'Web Studio 不支持 {{mode}} 认证模式。请使用 {{ov}} CLI 或 Python SDK 连接此服务器。',
        primary: '该服务器配置了 {{mode}} 认证。',
        title: '不支持的认证模式',
      },
      userHint: '供 Playground 和租户数据 API 使用。',
    },
    connectionPage: {
      description: '配置 OpenViking 服务连接、控制面凭证和当前数据访问凭证。',
      title: '连接设置',
    },
    dialogs: {
      addAccount: {
        description:
          '创建一个工作区 account 和第一个 admin user。新 key 只会在创建后展示一次。',
        title: '新增 account',
      },
      addUser: {
        currentAccountDescription:
          '在 {{accountId}} 空间下创建用户。生成的 key 只会在创建后展示一次。',
        description:
          '在已有 account 下注册 user。生成的 key 只会在创建后展示一次。',
        title: '新增 user',
      },
      changeRole: {
        description:
          '将 {{account}} / {{user}} 的角色修改为 {{role}}。新的权限会立即生效。',
        title: '修改用户角色？',
      },
      regenerate: {
        description:
          '要重新生成 {{account}} / {{user}} 的 API key 吗？当前 key 会立即失效。',
        title: '重新生成 API key？',
      },
      removeUser: {
        description:
          '确定从 {{account}} 空间移除 {{user}} 吗？该用户的 API Key 会立即失效，此操作不可撤销。',
        title: '删除用户？',
      },
    },
    empty: {
      adminDescription:
        '使用 root 或 account admin API key 后，可以列出用户、复制 key、新增身份或轮换凭证。',
      adminTitle: '需要 admin 权限',
      usersDescription: '创建一个 user 来生成第一个 API key。',
      usersTitle: '选中的 accounts 下没有 user',
    },
    fields: {
      account: 'Account',
      adminUser: 'Admin user',
      adminApiKey: 'Admin API key',
      apiKey: 'API key',
      baseUrl: '服务地址',
      dataApiKey: 'User API key',
      rootApiKey: 'Root or Admin API Key',
      userApiKey: 'User API Key',
      role: '角色',
      user: 'User',
    },
    health: {
      admin: '控制面权限',
      data: '数据访问',
      state: {
        checking: '检查中',
        error: '异常',
        ok: '正常',
        skipped: '未检查',
      },
    },
    keyResult: {
      description:
        '请现在复制保存。离开当前状态后，OpenViking 可能只展示前缀。',
      dismiss: '收起',
      title: '新的 API key',
    },
    loading: '正在加载身份...',
    management: {
      accountFilter: 'Accounts',
      accessDeniedDescription:
        '只有配置并通过校验的 Root 或 Account Admin API Key 才能管理用户。',
      accessDeniedTitle: '无用户管理权限',
      currentAccountDescription: '管理 {{account}} 空间下的用户和访问凭证。',
      description:
        '查看选中 accounts 下的 users 和凭证，并在网页端新增 user 或轮换 key。',
      memberListDescription:
        '“切换身份”会将该用户设为 Playground、检索等数据页面的访问身份，不会改变当前 Root/Admin 管理凭证。',
      memberListDescriptionRoot:
        '可直接修改成员角色；“切换身份”只会改变 Playground、检索等数据页面的访问身份，不会改变当前 Root 管理凭证。',
      memberListTitle: '空间成员',
      cannotRemoveCurrentIdentity: '不能删除当前正在使用的身份。',
      cannotRemoveLastManager: '不能删除空间内最后一个管理员。',
      noUsableKey: '该用户没有可用于数据访问的明文 API Key。',
      openConnection: '打开连接设置',
      title: '用户管理',
    },
    page: {
      adminDescription:
        '配置当前 OpenViking Studio 身份，并管理账号、用户和 API key。',
      description:
        '配置当前 OpenViking Studio 的服务地址和 API key，查看当前身份下的数据。',
      title: '连接与身份',
    },
    placeholders: {
      account: 'team-account',
      adminApiKey: 'Root 或 account-admin key',
      apiKey: '输入 X-API-Key 或 Bearer token',
      baseUrl: 'http://127.0.0.1:1933',
      devModeApiKey: '[dev mode，无需 API key]',
      userApiKey: 'User API key',
      user: 'default',
    },
    roles: {
      admin: 'Admin',
      root: 'Root',
      user: 'User',
    },
    serverMode: {
      api_key: 'API key 模式',
      checking: '检查中...',
      dev: '开发模式',
      ldap: 'LDAP 模式',
      offline: '离线',
      oidc: 'OIDC 模式',
      trusted: 'Trusted 模式',
    },
    stats: {
      accounts: 'Accounts 总数',
      apiKeys: '可见 API keys',
      users: 'Users',
    },
    table: {
      account: 'Account',
      actions: '操作',
      apiKey: 'API key',
      role: '角色',
      user: 'User',
    },
    toast: {
      accountCreated: 'Account 已创建',
      connectionSaved: '连接已保存',
      copyFailed: '复制失败',
      copied: '已复制',
      dataKeySelected: '已切换数据访问身份',
      keyRegenerated: 'API key 已重新生成',
      roleUpdated: '{{user}} 的角色已修改为 {{role}}',
      userCreated: 'User 已创建',
      userRemoved: '{{user}} 已删除',
    },
  },
} as const

export default settings
