import { queryOptions, useQuery } from '@tanstack/vue-query'
import { toValue, type MaybeRefOrGetter } from 'vue'

import type { Period } from '@/lib/radarQuery'

import { api, type Schemas } from './client'

type OpportunityList = Schemas['OpportunityList']
type Opportunity = Schemas['Opportunity']
type Evidence = Schemas['Evidence']
type TopicEvidence = Schemas['TopicEvidence']
type OpportunityTimeline = Schemas['OpportunityTimeline']

// Lo que una sección necesita de su consulta (mini barras, evidencia y evolución del expediente)
// para pintar su estado sin depender del tipo interno de TanStack Query.
export interface QueryState<T> {
  data: T | undefined
  isPending: boolean
  isError: boolean
}

// Solo con el flag explícito: si la API falla, la vista muestra el error y nunca cae a los
// fixtures, que se leerían como datos reales (CLAUDE.md §2.3).
export const USING_FIXTURES = import.meta.env.VITE_USE_FIXTURES === 'true'

// Un tema puede desaparecer entre ejecuciones de `analyze`: la API responde 404 y la vista lo dice.
const HTTP_NOT_FOUND = 404

async function loadFixture() {
  const fixture = await import('@fixtures/opportunities.json')
  // El JSON se generó contra el schema de Opportunity y opportunities.spec.ts lo vigila.
  return {
    list: fixture.default.opportunities as OpportunityList,
    evidence: fixture.default.evidence as Record<string, Evidence[]>,
    timeline: fixture.default.timeline as Record<string, OpportunityTimeline>,
  }
}

async function fetchOpportunities(period: Period): Promise<OpportunityList | null> {
  const { data, error } = await api.GET('/api/v1/opportunities', {
    params: { query: { period } },
  })
  if (error !== undefined || data === undefined) throw new Error('GET /opportunities falló')
  return data
}

async function fetchOpportunity(id: string): Promise<Opportunity | null> {
  if (USING_FIXTURES) {
    const { list } = await loadFixture()
    return list.items.find((item) => item.id === id) ?? null
  }
  const { data, error, response } = await api.GET('/api/v1/opportunities/{opportunity_id}', {
    params: { path: { opportunity_id: id } },
  })
  if (response.status === HTTP_NOT_FOUND) return null
  if (error !== undefined || data === undefined) throw new Error('GET /opportunities/{id} falló')
  return data
}

async function fetchEvidence(id: string): Promise<Evidence[]> {
  if (USING_FIXTURES) return (await loadFixture()).evidence[id] ?? []
  const { data, error } = await api.GET('/api/v1/opportunities/{opportunity_id}/evidence', {
    params: { path: { opportunity_id: id } },
  })
  if (error !== undefined || data === undefined) {
    throw new Error('GET /opportunities/{id}/evidence falló')
  }
  return data
}

async function fetchTimeline(id: string): Promise<OpportunityTimeline | null> {
  if (USING_FIXTURES) return (await loadFixture()).timeline[id] ?? null
  const { data, error, response } = await api.GET(
    '/api/v1/opportunities/{opportunity_id}/timeline',
    { params: { path: { opportunity_id: id } } },
  )
  if (response.status === HTTP_NOT_FOUND) return null
  if (error !== undefined || data === undefined) {
    throw new Error('GET /opportunities/{id}/timeline falló')
  }
  return data
}

async function fetchAllEvidence(): Promise<TopicEvidence[] | null> {
  if (USING_FIXTURES) {
    const { evidence } = await loadFixture()
    return Object.entries(evidence).flatMap(([id, pieces]) =>
      pieces.map((piece) => ({ ...piece, opportunity_id: id })),
    )
  }
  const { data, error } = await api.GET('/api/v1/evidence')
  if (error !== undefined || data === undefined) throw new Error('GET /evidence falló')
  return data
}

async function fetchAllTimelines(): Promise<OpportunityTimeline[] | null> {
  if (USING_FIXTURES) return Object.values((await loadFixture()).timeline)
  const { data, error } = await api.GET('/api/v1/timelines')
  if (error !== undefined || data === undefined) throw new Error('GET /timelines falló')
  return data
}

function opportunityQueryOptions(id: string) {
  return queryOptions({ queryKey: ['opportunity', id], queryFn: () => fetchOpportunity(id) })
}

function evidenceQueryOptions(id: string) {
  return queryOptions({
    queryKey: ['opportunity', id, 'evidence'],
    queryFn: () => fetchEvidence(id),
  })
}

function timelineQueryOptions(id: string) {
  return queryOptions({
    queryKey: ['opportunity', id, 'timeline'],
    queryFn: () => fetchTimeline(id),
  })
}

export function useOpportunities(period: MaybeRefOrGetter<Period>) {
  return useQuery({
    queryKey: ['opportunities', period],
    queryFn: async () =>
      USING_FIXTURES ? (await loadFixture()).list : fetchOpportunities(toValue(period)),
  })
}

export function useOpportunity(id: MaybeRefOrGetter<string>) {
  return useQuery(() => opportunityQueryOptions(toValue(id)))
}

export function useOpportunityEvidence(id: MaybeRefOrGetter<string>) {
  return useQuery(() => evidenceQueryOptions(toValue(id)))
}

export function useOpportunityTimeline(id: MaybeRefOrGetter<string>) {
  return useQuery(() => timelineQueryOptions(toValue(id)))
}

// Explorar y la paleta comparten la clave: lo que cargó uno lo reutiliza el otro.
export function useAllEvidence(enabled: MaybeRefOrGetter<boolean> = true) {
  return useQuery(() => ({
    queryKey: ['evidence'],
    queryFn: fetchAllEvidence,
    enabled: toValue(enabled),
  }))
}

// Sin ejecución de `analyze` (`null`) el mapa queda vacío y cada fila dice que no hay dato.
export function useAllTimelines() {
  return useQuery({
    queryKey: ['timelines'],
    queryFn: fetchAllTimelines,
    select: (timelines) =>
      new Map((timelines ?? []).map((timeline) => [timeline.opportunity_id, timeline])),
  })
}
