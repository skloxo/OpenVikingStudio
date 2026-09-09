export const settings = {
  settings: {
    hub: {
      title: 'Unified Settings & Data Ops Hub',
      description: 'Centralized management of credentials, model endpoints, privacy redaction rules, and OVPack data operations.',
      tabs: {
        general: 'General & Server',
        privacy: 'Privacy & Redaction',
        dataOps: 'OVPack & Data Ops',
      },
      models: {
        title: 'Models & Vector Endpoints',
        description: 'Real-time observability of underlying VLM, Embedding vector engines, and Rerank reordering models',
        activeGroup: 'Configured Models',
        vlm: 'VLM Multimodal Model',
        embedding: 'Embedding Vector Engine',
        rerank: 'Rerank Reordering Engine',
        compressor: 'Context Compressor',
        dimension: 'Dimensions',
        provider: 'Provider',
        status: 'Endpoint Status',
        healthy: 'Ready',
        noModels: 'No custom model endpoints detected; default rule set is active',
        calls: 'Calls',
        tokens: 'Tokens',
        lastUpdated: 'Last Updated',
        noActiveModel: 'No active model data',
      },
      workspace: {
        title: 'Workspace & Storage',
        description: 'Underlying VikingFS filesystem storage paths and default ingest targets',
        rootUri: 'Root Filesystem URI',
        defaultResourceTarget: 'Default Resource Ingest Target',
        defaultSkillTarget: 'Default Skill Ingest Target',
        storageEngine: 'Storage Engine',
        vikingfsDesc: 'AGFS tiered storage and atomic snapshot protection enabled',
      },
      privacy: {
        title: 'Privacy & Data Redaction Hub',
        description: 'End-to-end sensitive data filtering, PII masking, and custom rule enforcement',
        categories: 'Redaction Categories',
        toggleMask: 'Global Credential Masking',
        toggleMaskDesc: 'Automatically mask API keys and security tokens in request and log payloads',
        piiMask: 'PII Personal Privacy Masking',
        piiMaskDesc: 'Automatically detect and mask emails, phone numbers, and IP addresses with asterisks',
        activeRules: 'Active Rules Count',
        playgroundTitle: 'Live Redaction Playground',
        playgroundDesc: 'Input sample text with sensitive tokens to preview real-time sanitization output',
        inputLabel: 'Sample Input Text',
        inputPlaceholder: 'Enter test text, e.g., Authorization: Bearer sk-99887766aabbccdd, contact: fsk@8.129.0.26',
        previewBtn: 'Preview Redaction',
        previewOutput: 'Sanitized Output',
        rulesTableTitle: 'Pattern Matching Rules',
        ruleName: 'Rule Category',
        rulePattern: 'Pattern / Field',
        ruleAction: 'Policy Action',
        actionMask: 'Hash / Star Masking',
        actionRedact: 'Physical Truncation',
      },
      dataOps: {
        title: 'Knowledge Brain Backup & Migration (OVPack)',
        description: 'One-click full snapshots, scoped resource export, knowledge pack migration, and disaster recovery via .ovpack',
        exportTitle: 'Pack & Export (OVPack)',
        exportDesc: 'Package specified Viking URI hierarchy into a self-contained .ovpack archive',
        targetUriLabel: 'Target Viking URI',
        targetUriPlaceholder: 'viking://resources/ or viking://',
        quickScopes: 'Common Scopes:',
        includeVectors: 'Include Vector Snapshots',
        includeVectorsHint: 'Bundles vector indexes to accelerate post-migration recall, slightly increases pack size',
        exportBtn: 'Export .ovpack',
        exporting: 'Exporting archive...',
        backupTitle: 'System Full Snapshot Backup',
        backupDesc: 'Backs up all public scopes and complete system states into a disaster-recovery snapshot',
        backupBtn: 'Full System Backup',
        backingUp: 'Generating full snapshot...',
        importTitle: 'Knowledge Pack Import & Restore',
        importDesc: 'Upload an .ovpack archive to merge into target hierarchy, or execute a disaster restore',
        selectPackLabel: 'Select .ovpack archive',
        selectPackBtn: 'Choose Archive File',
        parentUriLabel: 'Mount Parent URI',
        conflictPolicy: 'Conflict Policy',
        conflictFail: 'Fail on Conflict',
        conflictOverwrite: 'Overwrite Existing',
        conflictSkip: 'Skip Existing',
        vectorMode: 'Vector Processing Mode',
        vectorAuto: 'Auto Detect',
        vectorRecompute: 'Recompute Vectors',
        vectorRequire: 'Require Existing Vectors',
        importBtn: 'Import Knowledge Pack',
        importing: 'Uploading and importing...',
        restoreBtn: 'Restore Full System Snapshot',
        restoring: 'Restoring snapshot...',
        restoreWarning: 'Warning: Full restore will overwrite current system data. Ensure you have backed up first!',
        restoreConfirm: 'Proceed with full system restore? This action cannot be undone.',
        successExport: 'Export download started successfully!',
        successBackup: 'Full backup download started successfully!',
        successImport: 'Successfully imported pack to {{uri}}!',
        successRestore: 'System snapshot restore completed!',
      },
    },
    actions: {
      addAccount: 'Add account',
      addUser: 'Add user',
      cancel: 'Cancel',
      changeRole: 'Change the role for {{user}}',
      confirmRemoveUser: 'Delete user',
      confirmRoleChange: 'Confirm change',
      copy: 'Copy',
      currentIdentity: 'Current identity',
      refresh: 'Refresh',
      regenerate: 'Regenerate',
      removeUser: 'Delete {{user}}',
      save: 'Save',
      switchIdentity: 'Switch identity',
      use: 'Use',
    },
    connection: {
      accountListLimited:
        'This key cannot list all accounts, but it can still manage the selected account if it has account-admin access.',
      adminError: 'Could not verify the Root API Key: {{message}}',
      description:
        'Use a User API Key for tenant data APIs and an optional Root or account-admin key for control APIs.',
      devMode:
        'Development mode is active — identity is automatic and no API key is required.',
      keyGuide: {
        control: {
          primary:
            'Your User API Key already enables the Playground and data access. Regular users do not need a control credential.',
          secondary:
            'To switch Accounts or manage users, request a Root Key from the deployment admin or an Admin Key from the current Account admin. The Root Key is stored at server.root_api_key in the server-side ov.conf.',
          title: 'Need to manage Accounts or users?',
        },
        data: {
          primary:
            'The Root/Admin API Key is mainly for management. The Playground and tenant data APIs require a User API Key bound to a user identity.',
          secondary:
            'Select or create a user in User Management, or regenerate its key, then use it as the User API Key.',
          title: 'A User API Key is still required',
        },
        empty: {
          primary:
            'Regular users should request a User API Key from their Account admin.',
          secondary:
            'Deployment admins can find the Root API Key at server.root_api_key in the server-side ov.conf. Add it here, then create or regenerate a User Key in User Management.',
          title: 'No OpenViking API Key yet?',
        },
        learnMore: 'Learn how to get an API Key',
        trusted: {
          primary:
            'This trusted server enforces Root Key validation. The browser needs the same Root API Key for management and tenant data requests.',
          secondary:
            'Request the Root Key from the deployment admin; it is stored at server.root_api_key in the server-side ov.conf. Trusted-mode data identity comes from Account/User assertions and does not need a User API Key.',
          title: 'This trusted server requires a Root API Key',
        },
      },
      rootHint: 'Lists accounts and users, and mints or rotates keys.',
      title: 'Connection settings',
      recheck: 'Re-check',
      rechecking: 'Re-checking service probe...',
      unsupportedAuthMode: {
        description:
          'Web Studio does not support the {{mode}} authentication mode. Please use the {{ov}} CLI or Python SDK to interact with this server.',
        primary: 'This server is configured with {{mode}} authentication.',
        title: 'Unsupported authentication mode',
      },
      userHint: 'Used by the Playground and tenant data APIs.',
    },
    connectionPage: {
      description:
        'Configure the OpenViking server connection, control credential, and active data credential.',
      title: 'Connection settings',
    },
    dialogs: {
      addAccount: {
        description:
          'Create a workspace account and its first admin user. The new key will be shown once.',
        title: 'Add account',
      },
      addUser: {
        currentAccountDescription:
          'Create a user in {{accountId}}. The generated key is shown only once.',
        description:
          'Register a user under an existing account. The generated key will be shown once.',
        title: 'Add user',
      },
      changeRole: {
        description:
          'Change the role for {{account}} / {{user}} to {{role}}. The new permissions take effect immediately.',
        title: 'Change user role?',
      },
      regenerate: {
        description:
          'Regenerate the API key for {{account}} / {{user}}. The current key stops working immediately.',
        title: 'Regenerate API key?',
      },
      removeUser: {
        description:
          'Remove {{user}} from {{account}}? Their API key stops working immediately. This action cannot be undone.',
        title: 'Delete user?',
      },
    },
    empty: {
      adminDescription:
        'Use a root or account admin API key to list users, copy keys, add identities, or regenerate credentials.',
      adminTitle: 'Admin access required',
      usersDescription: 'Create a user to mint the first API key.',
      usersTitle: 'No users in the selected accounts',
    },
    fields: {
      account: 'Account',
      adminUser: 'Admin user',
      adminApiKey: 'Admin API key',
      apiKey: 'API key',
      baseUrl: 'Server URL',
      dataApiKey: 'User API key',
      rootApiKey: 'Root or Admin API Key',
      userApiKey: 'User API Key',
      role: 'Role',
      user: 'User',
    },
    health: {
      admin: 'Admin control',
      data: 'Data access',
      state: {
        checking: 'Checking',
        error: 'Error',
        ok: 'OK',
        skipped: 'Not checked',
      },
    },
    keyResult: {
      description:
        'Copy it now. OpenViking may only show a prefix after you leave this state.',
      dismiss: 'Dismiss',
      title: 'New API key',
    },
    loading: 'Loading identities...',
    management: {
      accountFilter: 'Accounts',
      accessDeniedDescription:
        'User management requires a validated Root or Account Admin API key.',
      accessDeniedTitle: 'User management unavailable',
      currentAccountDescription:
        'Manage users and access credentials in the {{account}} workspace.',
      description:
        'Review users and credentials for selected accounts, then add users or rotate keys from the web UI.',
      memberListDescription:
        '"Switch identity" uses that user for data pages such as Playground and Retrieval without changing the active Root/Admin management credential.',
      memberListDescriptionRoot:
        'You can change member roles here. "Switch identity" only changes the user used by data pages such as Playground and Retrieval; it does not change the active Root management credential.',
      memberListTitle: 'Workspace members',
      cannotRemoveCurrentIdentity: 'The active identity cannot be deleted.',
      cannotRemoveLastManager:
        'The last workspace administrator cannot be deleted.',
      noUsableKey:
        'This user has no plaintext API key available for data access.',
      openConnection: 'Open connection settings',
      title: 'User management',
    },
    page: {
      adminDescription:
        'Configure the active OpenViking Studio identity and manage accounts, users, and API keys.',
      description:
        'Configure the OpenViking Studio server URL and API key, then view data for the current identity.',
      title: 'Connection & Identity',
    },
    placeholders: {
      account: 'team-account',
      adminApiKey: 'Root or account-admin key',
      apiKey: 'Enter X-API-Key or Bearer token',
      baseUrl: 'http://127.0.0.1:1933',
      devModeApiKey: '[dev mode, no api key required]',
      userApiKey: 'User API key',
      user: 'default',
    },
    roles: {
      admin: 'Admin',
      root: 'Root',
      user: 'User',
    },
    serverMode: {
      api_key: 'API key mode',
      checking: 'Checking...',
      dev: 'Development mode',
      ldap: 'LDAP mode',
      offline: 'Offline',
      oidc: 'OIDC mode',
      trusted: 'Trusted mode',
    },
    stats: {
      accounts: 'Total accounts',
      apiKeys: 'Visible API keys',
      users: 'Users',
    },
    table: {
      account: 'Account',
      actions: 'Actions',
      apiKey: 'API key',
      role: 'Role',
      user: 'User',
    },
    toast: {
      accountCreated: 'Account created',
      connectionSaved: 'Connection saved',
      copyFailed: 'Copy failed',
      copied: 'Copied',
      dataKeySelected: 'Data access identity switched',
      keyRegenerated: 'API key regenerated',
      roleUpdated: "{{user}}'s role changed to {{role}}",
      userCreated: 'User created',
      userRemoved: '{{user}} deleted',
    },
  },
} as const

export default settings
