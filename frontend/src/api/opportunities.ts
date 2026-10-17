import { useQuery } from '@tanstack/vue-query'
import { toValue, type MaybeRefOrGetter } from 'vue'

import type { Period } from '@/lib/radarQuery'

import { api, type Schemas } from './client'

type OpportunityList = Schemas['OpportunityList']

// Solo con el flag explícito: si la API falla, la vista muestra el error y nunca cae a los
// fixtures, que se leerían como datos reales (CLAUDE.md §2.3).
export const USING_FIXTURES = import.meta.env.VITE_USE_FIXTURES === 'true'

async function loadFixtureOpportunities(): Promise<OpportunityList> {
  const fixture = await import('@fixtures/opportunities.json')
  // El JSON se generó contra el schema de Opportunity y opportunities.spec.ts lo vigila.
  return fixture.default.opportunities as OpportunityList
}

async function fetchOpportunities(period: Period): Promise<OpportunityList | null> {
  const { data, error } = await api.GET('/api/v1/opportunities', {
    params: { query: { period } },
  })
  if (error !== undefined || data === undefined) throw new Error('GET /opportunities falló')
  return data
}

export function useOpportunities(period: MaybeRefOrGetter<Period>) {
  return useQuery({
    queryKey: ['opportunities', period],
    queryFn: () =>
      USING_FIXTURES ? loadFixtureOpportunities() : fetchOpportunities(toValue(period)),
  })
}
