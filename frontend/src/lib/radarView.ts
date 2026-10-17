import type { components } from '@/types/api'

import { LIFECYCLE_STYLE } from './lifecycle'
import type { Lifecycle, RadarQuery, RankingSort } from './radarQuery'

type Schemas = components['schemas']
type Opportunity = Schemas['Opportunity']
type OpportunityList = Schemas['OpportunityList']

export interface RankedOpportunity extends Opportunity {
  rank: number
}

export type PlottedOpportunity = RankedOpportunity & { audience_fit_score: number }

// Lo que la vista pinta, ya filtrado, ordenado y contado: los componentes solo lo leen.
export interface RadarView {
  total: number
  ranked: RankedOpportunity[]
  visible: RankedOpportunity[]
  isFiltered: boolean
  plotted: PlottedOpportunity[]
  unevaluatedCount: number
  dimmedIds: Set<string>
  selected: RankedOpportunity | null
  counts: { accelerating: number; emerging: number; latamGap: number }
}

// La pregunta del Radar son "los 10 temas que más crecen" (CLAUDE.md §1); si hay menos, la
// frase lo dice en lugar de rellenar el ranking (regla 3).
const EXPECTED_OPPORTUNITIES = 10

type RankingComparator = (a: RankedOpportunity, b: RankedOpportunity) => number

const byRank: RankingComparator = (a, b) => a.rank - b.rank

const RANKING_ORDER: Record<RankingSort, RankingComparator> = {
  opportunity: byRank,
  acceleration: (a, b) => b.acceleration - a.acceleration || byRank(a, b),
}

// El puesto es el orden en que llega la lista: el backend ya ordena por su ranking.
function rankInApiOrder(list: OpportunityList | null): RankedOpportunity[] {
  return (list?.items ?? []).map((opportunity, index) => ({ ...opportunity, rank: index + 1 }))
}

function hasFilters(query: RadarQuery): boolean {
  return query.lifecycle.length > 0 || query.gap
}

function matchesFilters(opportunity: Opportunity, query: RadarQuery): boolean {
  const stageMatches =
    query.lifecycle.length === 0 || query.lifecycle.includes(opportunity.lifecycle)
  const gapMatches = !query.gap || opportunity.latam_gap === true
  return stageMatches && gapMatches
}

// Sin encaje no hay posición en X: dibujarla en 0 se leería "encaje 0".
export function hasAudienceFit(opportunity: RankedOpportunity): opportunity is PlottedOpportunity {
  return opportunity.audience_fit_score != null
}

function collectDimmedIds(
  plotted: PlottedOpportunity[],
  visible: RankedOpportunity[],
  { highlight, selectedId }: { highlight: string[]; selectedId: string | undefined },
): Set<string> {
  const visibleIds = new Set(visible.map((opportunity) => opportunity.id))
  const isInFocus = (id: string) =>
    visibleIds.has(id) && (highlight.length === 0 || highlight.includes(id))
  const dimmed = plotted
    .map((opportunity) => opportunity.id)
    .filter((id) => id !== selectedId && !isInFocus(id))
  return new Set(dimmed)
}

function countVisible(visible: RankedOpportunity[]): RadarView['counts'] {
  return {
    accelerating: visible.filter((opportunity) => opportunity.lifecycle === 'accelerating').length,
    emerging: visible.filter((opportunity) => opportunity.lifecycle === 'emerging').length,
    latamGap: visible.filter((opportunity) => opportunity.latam_gap === true).length,
  }
}

export function buildRadarView(list: OpportunityList | null, query: RadarQuery): RadarView {
  const ranked = rankInApiOrder(list)
  const visible = ranked
    .filter((opportunity) => matchesFilters(opportunity, query))
    .sort(RANKING_ORDER[query.sort])
  const plotted = ranked.filter(hasAudienceFit)
  const selected =
    ranked.find((opportunity) => opportunity.id === query.selected) ?? ranked.at(0) ?? null
  return {
    total: ranked.length,
    ranked,
    visible,
    isFiltered: hasFilters(query),
    plotted,
    unevaluatedCount: ranked.length - plotted.length,
    dimmedIds: collectDimmedIds(plotted, visible, {
      highlight: query.highlight,
      selectedId: selected?.id,
    }),
    selected,
    counts: countVisible(visible),
  }
}

interface Noun {
  one: string
  many: string
}

const OPPORTUNITY_NOUN: Noun = { one: 'oportunidad', many: 'oportunidades' }
const TOPIC_NOUN: Noun = { one: 'tema', many: 'temas' }
const STAGE_SEPARATOR = ' o '
const FILTER_SEPARATOR = ' · '

function formatCount(count: number, noun: Noun): string {
  return `${count} ${count === 1 ? noun.one : noun.many}`
}

function stageLabel(lifecycle: Lifecycle): string {
  return LIFECYCLE_STYLE[lifecycle].label.toLowerCase()
}

function describeFilters(query: RadarQuery): string {
  const parts: string[] = []
  if (query.lifecycle.length > 0) {
    parts.push(`etapa ${query.lifecycle.map(stageLabel).join(STAGE_SEPARATOR)}`)
  }
  if (query.gap) parts.push('con hueco en LATAM')
  return parts.join(FILTER_SEPARATOR)
}

export function radarHeadline(view: RadarView, query: RadarQuery): string {
  if (hasFilters(query)) return `${view.visible.length} de ${formatCount(view.total, TOPIC_NOUN)}`
  return `${formatCount(view.total, OPPORTUNITY_NOUN)} esta semana`
}

export function radarSubline(view: RadarView, query: RadarQuery): string {
  if (hasFilters(query)) return `Filtro: ${describeFilters(query)}.`
  if (view.total < EXPECTED_OPPORTUNITIES) {
    return `Hay ${formatCount(view.total, TOPIC_NOUN)} con datos suficientes esta semana.`
  }
  return 'Los temas de IA que más rápido crecen, ordenados por su encaje con líderes y equipos de LATAM.'
}
