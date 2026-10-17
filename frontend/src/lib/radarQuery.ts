import type { LocationQuery, LocationQueryValue } from 'vue-router'

import type { components } from '@/types/api'

type Schemas = components['schemas']

export type Period = Schemas['Period']
export type Lifecycle = Schemas['Lifecycle']
export type Confidence = Schemas['Confidence']
export type Recommendation = Schemas['Recommendation']

// Los enums del contrato hacen falta en tiempo de ejecución para validar la URL; `satisfies`
// hace que el compilador avise si el contrato (src/types/api.ts) cambia y estos no.
export const PERIODS = ['24h', '7d', '30d'] as const satisfies readonly Period[]
export const LIFECYCLES = [
  'emerging',
  'accelerating',
  'peaking',
  'saturated',
  'unknown',
] as const satisfies readonly Lifecycle[]
export const CONFIDENCES = ['low', 'medium', 'high'] as const satisfies readonly Confidence[]
export const RECOMMENDATIONS = [
  'publish_now',
  'find_angle',
  'wait_for_case',
  'discard',
] as const satisfies readonly Recommendation[]

export const RANKING_SORTS = ['opportunity', 'acceleration'] as const
export type RankingSort = (typeof RANKING_SORTS)[number]

export const DEFAULT_PERIOD: Period = '7d'
export const DEFAULT_RANKING_SORT: RankingSort = 'opportunity'
const LIST_SEPARATOR = ','
const GAP_PARAM_ON = '1'

// La URL es la única fuente de verdad del estado del Radar: los filtros, el usuario y el
// agente de la app lo cambian igual, y cualquier estado se puede compartir y repetir.
export interface RadarQuery {
  period: Period
  lifecycle: Lifecycle[]
  confidence: Confidence | null
  topic: string | null
  selected: string | null
  highlight: string[]
  gap: boolean
  sort: RankingSort
  recommendation: Recommendation | null
}

export const RADAR_QUERY_KEYS = [
  'period',
  'lifecycle',
  'confidence',
  'topic',
  'selected',
  'highlight',
  'gap',
  'sort',
  'recommendation',
] as const satisfies readonly (keyof RadarQuery)[]

function firstValue(value: LocationQueryValue | LocationQueryValue[] | undefined): string | null {
  const first = Array.isArray(value) ? value[0] : value
  return first || null
}

function listValue(value: LocationQueryValue | LocationQueryValue[] | undefined): string[] {
  const list = firstValue(value)
  return list ? list.split(LIST_SEPARATOR).filter(Boolean) : []
}

function oneOf<T extends string>(allowed: readonly T[], value: string | null): T | null {
  return allowed.find((option) => option === value) ?? null
}

function uniqueOf<T extends string>(allowed: readonly T[], values: string[]): T[] {
  const valid = values.map((value) => oneOf(allowed, value)).filter((value) => value !== null)
  return [...new Set(valid)]
}

// Quita filtros y resaltados; la selección, el periodo y el orden se conservan. El `reset_view`
// del agente (backend/app/agent/tools.py) quita lo mismo.
export function resetViewPatch(): Partial<RadarQuery> {
  return {
    lifecycle: [],
    gap: false,
    highlight: [],
    recommendation: null,
    confidence: null,
    topic: null,
  }
}

export function parseRadarQuery(query: LocationQuery): RadarQuery {
  return {
    period: oneOf(PERIODS, firstValue(query.period)) ?? DEFAULT_PERIOD,
    lifecycle: uniqueOf(LIFECYCLES, listValue(query.lifecycle)),
    confidence: oneOf(CONFIDENCES, firstValue(query.confidence)),
    topic: firstValue(query.topic),
    selected: firstValue(query.selected),
    highlight: listValue(query.highlight),
    gap: firstValue(query.gap) === GAP_PARAM_ON,
    sort: oneOf(RANKING_SORTS, firstValue(query.sort)) ?? DEFAULT_RANKING_SORT,
    recommendation: oneOf(RECOMMENDATIONS, firstValue(query.recommendation)),
  }
}

export function serializeRadarQuery(state: RadarQuery): Record<string, string> {
  const params: Record<string, string> = {}
  if (state.period !== DEFAULT_PERIOD) params.period = state.period
  if (state.lifecycle.length > 0) params.lifecycle = state.lifecycle.join(LIST_SEPARATOR)
  if (state.confidence) params.confidence = state.confidence
  if (state.topic) params.topic = state.topic
  if (state.selected) params.selected = state.selected
  if (state.highlight.length > 0) params.highlight = state.highlight.join(LIST_SEPARATOR)
  if (state.gap) params.gap = GAP_PARAM_ON
  if (state.sort !== DEFAULT_RANKING_SORT) params.sort = state.sort
  if (state.recommendation) params.recommendation = state.recommendation
  return params
}
