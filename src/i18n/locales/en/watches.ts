export const watches = {
  watchesPage: {
    title: 'Scheduled Sync',
    description:
      'Keep remote resources current with recurring Watch tasks and manage their schedules.',
    refresh: 'Refresh',
    add: 'Add',
    adding: 'Adding...',
    loading: 'Loading scheduled syncs...',
    loadFailed: 'Could not load scheduled syncs',
    empty: 'No scheduled syncs',
    emptyDescription:
      'Add a remote resource and enable scheduled sync to get started.',
    never: 'Not synced yet',
    cancel: 'Cancel',
    save: 'Save',
    deleteConfirm: 'Delete',
    creation: {
      title: 'Creating scheduled sync',
      description:
        'The resource was submitted in the background. The list will refresh automatically.',
    },
    columns: {
      resource: 'Resource',
      source: 'Source',
      status: 'Status',
      interval: 'Interval',
      lastRun: 'Last sync',
      nextRun: 'Next sync',
      actions: 'Actions',
    },
    status: {
      active: 'Enabled',
      disabled: 'Disabled',
    },
    actions: {
      trigger: 'Sync now',
      syncing: 'Syncing...',
      disable: 'Disable',
      enable: 'Enable',
      more: 'More',
      history: 'Processing history',
      edit: 'Edit',
      delete: 'Delete',
    },
    interval: {
      minutes_one: 'Every minute',
      minutes_other: 'Every {{count}} minutes',
      hours_one: 'Every hour',
      hours_other: 'Every {{count}} hours',
      days_one: 'Every day',
      days_other: 'Every {{count}} days',
    },
    addDialog: {
      title: 'Add scheduled sync',
      description:
        'Add a remote resource and configure how often OpenViking checks for updates.',
      sourceUrl: 'Remote URL',
      sourcePlaceholder: 'https://github.com/org/repo',
      targetUri: 'Target URI (optional)',
      targetPlaceholder: 'viking://resources/docs/',
      submit: 'Create Watch',
    },
    editDialog: {
      title: 'Edit scheduled sync',
      interval: 'Interval (minutes)',
      intervalHint: 'For example, 60 for hourly or 1440 for daily.',
      reason: 'Reason (optional)',
      reasonPlaceholder: 'Why should this resource stay synchronized?',
      instruction: 'Processing instruction (optional)',
      instructionPlaceholder:
        'Special processing instructions for this resource.',
    },
    deleteDialog: {
      title: 'Delete scheduled sync?',
      description:
        'The resource {{uri}} will remain available, but it will no longer update automatically.',
    },
    history: {
      title: 'Processing history',
      description:
        'Background tasks filtered by this resource. Results may include the initial import, manual processing, and scheduled syncs.',
      loading: 'Loading processing history...',
      loadFailed: 'Could not load processing history',
      empty: 'No processing history',
      emptyDescription:
        'No background processing tasks were found for this resource.',
      stage: 'Stage',
    },
    toast: {
      creating: 'Creating scheduled sync. Please wait...',
      created: 'Scheduled sync added',
      createFailed: 'Failed to create scheduled sync',
      createTimeout: 'The new task is not visible yet. Refresh again shortly.',
      updated: 'Scheduled sync updated',
      triggered: 'Sync scheduled',
      deleted: 'Scheduled sync deleted',
    },
  },
} as const

export default watches
