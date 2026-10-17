import { createFileRoute, redirect } from '@tanstack/react-router'

interface ResourcesSearch {
  uri?: string
  file?: string
  search?: string
}

export const Route = createFileRoute('/resources')({
  validateSearch: (search: Record<string, unknown>): ResourcesSearch => ({
    uri: typeof search.uri === 'string' ? search.uri : undefined,
    file: typeof search.file === 'string' ? search.file : undefined,
    search: typeof search.search === 'string' ? search.search : undefined,
  }),
  beforeLoad: ({ search }) => {
    throw redirect({
      to: '/playground',
      search: {
        uri: search.uri || search.search,
        file: search.file,
      },
    })
  },
  component: () => null,
})

