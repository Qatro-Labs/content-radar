import { useQuery } from '@tanstack/vue-query'

import { api, type Schemas } from './client'

type SourceStatus = Schemas['SourceStatus']

export function latestObservation(sources: SourceStatus[]): string | null {
  const observed = sources
    .map((source) => source.last_observed_at)
    .filter((observedAt): observedAt is string => observedAt != null)
  if (observed.length === 0) return null
  return observed.reduce((latest, current) =>
    Date.parse(current) > Date.parse(latest) ? current : latest,
  )
}

async function fetchSourcesStatus(): Promise<SourceStatus[]> {
  const { data, error } = await api.GET('/api/v1/sources/status')
  if (error !== undefined || data === undefined) throw new Error('GET /sources/status falló')
  return data
}

export function useLatestObservation() {
  return useQuery({
    queryKey: ['sources', 'status'],
    queryFn: fetchSourcesStatus,
    select: latestObservation,
  })
}
