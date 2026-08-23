import { createFileRoute, redirect } from '@tanstack/react-router'
import { z } from 'zod'

const resourcesSearchSchema = z.object({
  uri: z.string().optional(),
  file: z.string().optional(),
  search: z.string().optional(),
})

export const Route = createFileRoute('/resources')({
  validateSearch: resourcesSearchSchema,
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

