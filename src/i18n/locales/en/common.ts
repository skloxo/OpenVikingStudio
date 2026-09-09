export const common = {
  common: {
    action: {
      cancel: 'Cancel',
      saveConnection: 'Save Connection',
      showAdvancedIdentityFields: 'Show Advanced Identity Fields',
    },
    errorBoundary: {
      description:
        'An unhandled exception occurred while rendering the route. Try again first; if it persists, inspect the error details below.',
      reload: 'Reload Page',
      retry: 'Retry',
      title: 'Something went wrong',
    },
    language: {
      current: 'Current',
      label: 'Language',
    },
    theme: {
      toggle: 'Toggle theme',
    },
  },
  appShell: {
    footer: {
      agentIntegrations: 'Agent Integrations',
      connection: 'Connection Settings',
      docs: 'Documentation',
      github: 'GitHub',
      sdkApi: 'SDK & API',
      users: 'User Management',
    },
    header: {
      currentUser: {
        account: 'Account',
        accountSummary: 'Account · {{account}}',
        loadingUsers: 'Loading users',
        loadUsersFailed: 'Failed to load users',
        noUsers: 'No users in this account',
        openMenu: 'View current user {{user}}',
        retry: 'Retry',
        signedInAs: 'Current data identity',
        switchSuccess: 'User switched',
        switchAction: 'Switch user',
        switchUser: 'Switch user',
        unset: 'Not set',
        user: 'User',
        userId: 'User ID',
        userIdPlaceholder: 'Enter a User ID',
      },
      defaultTitle: 'OpenViking Studio',
    },
    navigation: {
      home: {
        title: 'System Home',
      },
      crossDeviceVerify: {
        title: 'OAuth verify',
      },
      operations: {
        title: 'Operations',
      },
      requestLogs: {
        title: 'Request Logs',
      },
      monitoring: {
        title: 'System Monitoring',
      },
      skills: {
        title: 'Skills',
      },
      harnessLogs: {
        title: 'Harness Audit',
      },
      resources: {
        title: 'Resources',
      },
      graph: {
        title: 'Knowledge Graph',
      },
      tasks: {
        title: 'Task Center',
      },
      retrieval: {
        title: 'Information Governance',
      },
      sessions: {
        title: 'Session Center',
      },
      users: {
        title: 'User Management',
      },
      settings: {
        title: 'Settings',
      },
      playground: {
        title: 'Interactive Playground',
      },
    },
    sidebar: {
      groups: {
        operations: 'Activity',
        resources: 'Resources',
        settings: 'Settings',
        workspace: 'Workspace',
      },
      loadingSessions: 'Loading...',
      noSessions: 'No sessions',
      workspaceGroupLabel: 'OpenViking Studio',
      doctorPill: '1933 RPC Healthy',
      doctorPillTooltip: 'Click to open System Health Probe & Auto-Heal Panel',
    },
    doctor: {
      title: 'OpenViking System Health Probe & Auto-Heal Hub',
      description: 'Real-time probe for 1933 RPC service, AGFS virtual file system mount, VectorDB engine, and access guard, supporting one-click physical self-healing.',
      statusHealthy: '1933 RPC Healthy',
      statusAbnormal: 'Abnormal',
      recheck: 'Re-probe',
      healNow: 'Auto-Heal (Run Doctor)',
      healing: 'Healing ({{step}}/3)...',
      healSuccess: 'System self-healing completed, all services optimal',
      probing: 'Probing backend heartbeat...',
      lastCheck: 'Last check',
      terminalLogs: 'Doctor Pipeline Logs',
    },
  },
  accountSwitcher: {
    create: 'Create account',
    dialog: {
      accountLabel: 'Account',
      accountPlaceholder: 'team-account',
      adminLabel: 'Initial admin user',
      cancel: 'Cancel',
      description:
        'Create a workspace and its first administrator. Studio switches to it after creation.',
      submit: 'Create and switch',
      title: 'Create account',
    },
    empty: 'No matching accounts',
    errors: {
      loadAccounts: 'Could not load accounts',
      noCreatedKey:
        'The account was created, but the server did not return a data credential.',
      noUsableKey:
        'This account has no plaintext user API key available for data access.',
      noUsers: 'This account has no available users.',
    },
    loading: 'Loading accounts...',
    manualSwitch: {
      description:
        'The server did not expose a plaintext credential for {{account}}. Enter a User API Key from that account.',
      hint: 'Studio only verifies the key and switches the active data identity. It will not modify or rotate the server credential.',
      keyLabel: 'User API Key',
      keyPlaceholder: 'Paste a User API Key for the target account',
      manageOnly: 'Manage without a User Key',
      submit: 'Verify and switch',
      title: 'Enter a User API Key',
    },
    memberCount: '{{count}} users',
    searchPlaceholder: 'Search accounts',
    toast: {
      created: 'Created and switched to {{account}}',
      createdSwitchFailed:
        'Created {{account}}, but data identity switching failed: {{error}}. The Account remains available for management.',
      managementSwitched:
        'Switched management to {{account}}. Select or create a User Key before opening tenant data.',
      switched: 'Switched to {{account}}',
    },
    unset: 'No account selected',
  },
  connection: {
    devMode: {
      description:
        'This server provides identity automatically, so account, user, and API key are usually not required.',
      title: 'Server-managed identity',
    },
    dialog: {
      title: 'Connection & Identity',
    },
    identitySummary: {
      dev: 'Server-managed identity',
      named: '{{identity}}',
      unset: 'Identity not set',
    },
    fields: {
      accountId: {
        label: 'Account',
        placeholder: 'default',
      },
      apiKey: {
        label: 'API Key',
        placeholder: 'Enter X-API-Key or Bearer token',
      },
      adminApiKey: {
        label: 'Admin API key',
        placeholder: 'Root or account-admin key',
      },
      baseUrl: {
        label: 'Service URL',
        placeholder: 'http://127.0.0.1:1933',
      },
      credentials: {
        title: 'Identity & Credentials',
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
      useCurrent: 'Authorize as the current identity',
      noCurrent:
        'No identity set. Open Connection & Identity to sign in first, or use a different API key below.',
      useSelect: 'Authorize a specific account / user',
      selectAccountLabel: 'Account',
      selectUserLabel: 'User',
      selectNoKey:
        'This user has no API key. Pick another user or regenerate a key in Connection & Identity.',
      selectAccountAdminHint:
        'You can authorize users in your own account only.',
      useCustom: 'Use a different API key',
      customKeyLabel: 'API key',
      customKeyPlaceholder: 'Paste an API key (not persisted)',
    },
    consent: {
      title: 'Authorize {{clientName}}',
      loading: 'Loading authorization request…',
      expired:
        'This authorization has expired or is no longer valid. Restart the flow from your MCP client.',
      missingPending:
        'Missing authorization id. Open the link your MCP client gave you.',
      requestSummary:
        '{{clientName}} is requesting access to your OpenViking workspace.',
      redirectLabel: 'Redirect',
      scopesLabel: 'Scopes',
      scopesNone: '(none)',
      signInRequired:
        'Sign in to OpenViking Studio (Connection & Identity) or paste an API key below to authorize this client.',
      openConnectionSettings: 'Open Connection & Identity',
      authorize: 'Authorize',
      deny: 'Deny',
      useAnotherDevice: 'Use another device →',
      waitingRedirect: 'Authorized — redirecting back to the client…',
      verifying: 'Verifying…',
      denying: 'Denying…',
      denied: 'Denied. You can close this tab.',
      verifyError: 'Authorization failed: {{message}}',
      noApiKey: 'No API key available. Select an identity or paste a key.',
    },
    verify: {
      title: 'Cross-device verify',
      description:
        'Enter the 6-character code shown on the device that started the MCP client login.',
      codeLabel: 'Verification code',
      codePlaceholder: '6-character code',
      submit: 'Authorize',
      success:
        'Authorized for {{clientName}}. You can close this tab and return to the original device.',
      successUnknownClient:
        'Authorized. You can close this tab and return to the original device.',
      verifyError: 'Authorization failed: {{message}}',
      noApiKey: 'No API key available. Select an identity or paste a key.',
      signInRequired:
        'Sign in to OpenViking Studio (Connection & Identity) or paste an API key below to verify.',
    },
  },
} as const

export default common
