import type { components } from '@/types/api'

import { countLabel } from './evidenceFormat'
import { formatUtcTimestamp } from './format'
import { LIFECYCLE_STYLE } from './lifecycle'
import { CONFIDENCE_LABEL, RECOMMENDATION_LABEL } from './opportunityFormat'
import {
  resetViewPatch,
  type Lifecycle,
  type RadarQuery,
  type RankingSort,
  type Recommendation,
} from './radarQuery'

type Schemas = components['schemas']
type Opportunity = Schemas['Opportunity']
type OpportunityList = Schemas['OpportunityList']

export interface RankedOpportunity extends Opportunity {
  rank: number
}

export type PlottedOpportunity = RankedOpportunity & { audience_fit_score: number }

export const COUNTER_FILTERS = ['publish_now', 'accelerating', 'emerging', 'unknown'] as const
export type CounterFilter = (typeof COUNTER_FILTERS)[number]

// D9 del plan fe-dashboard-v2: sin temas «Publicar ya», «Esta semana» enseña los primeros del
// ranking y lo dice.
export interface WeekPicks {
  topics: RankedOpportunity[]
  hasPublishNow: boolean
}

// Lo que la vista pinta, ya filtrado, ordenado y contado: los componentes solo lo leen.
export interface RadarView {
  total: number
  ranked: RankedOpportunity[]
  visible: RankedOpportunity[]
  isFiltered: boolean
  plotted: PlottedOpportunity[]
  // Temas con encaje: los que podrían ir en el radar si no hubiera límite.
  plottableCount: number
  unevaluatedCount: number
  dimmedIds: Set<string>
  selected: RankedOpportunity | null
  // Totales fijos sobre todos los temas (D2): con selección única, contar lo filtrado dejaría
  // los demás contadores a 0.
  counts: { publishNow: number; accelerating: number; emerging: number; unknown: number }
  activeCounter: CounterFilter | null
  weekPicks: WeekPicks
  outlierPieces: number
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
  return (
    query.lifecycle.length > 0 ||
    query.gap ||
    query.recommendation !== null ||
    query.confidence !== null ||
    query.topic !== null
  )
}

// Igual que `_matches` de backend/app/services/opportunities.py: el tema, por subcadena sin
// distinguir mayúsculas.
function topicMatches(opportunity: Opportunity, topic: string | null): boolean {
  return topic === null || opportunity.topic.toLowerCase().includes(topic.toLowerCase())
}

function matchesFilters(opportunity: Opportunity, query: RadarQuery): boolean {
  const stageMatches =
    query.lifecycle.length === 0 || query.lifecycle.includes(opportunity.lifecycle)
  const gapMatches = !query.gap || opportunity.latam_gap === true
  const recommendationMatches =
    query.recommendation === null || opportunity.recommendation === query.recommendation
  const confidenceMatches = query.confidence === null || opportunity.confidence === query.confidence
  return (
    stageMatches &&
    gapMatches &&
    recommendationMatches &&
    confidenceMatches &&
    topicMatches(opportunity, query.topic)
  )
}

// Sin encaje no hay posición en X: dibujarla en 0 se leería "encaje 0".
export function hasAudienceFit(opportunity: RankedOpportunity): opportunity is PlottedOpportunity {
  return opportunity.audience_fit_score != null
}

// Sin filtros el radar enseña los primeros por oportunidad (18/10): con todos, «Poca señal» se
// llena de temas que no aportan. Un filtro, la selección o un resaltado de Rad añaden los suyos.
export const RADAR_TOP = 25

interface RadarOptions {
  // `null`: sin límite («Ver todos»).
  radarTop?: number | null
}

function pickPlotted(
  ranked: RankedOpportunity[],
  visible: RankedOpportunity[],
  query: RadarQuery,
  radarTop: number | null,
): PlottedOpportunity[] {
  const plottable = ranked.filter(hasAudienceFit)
  if (radarTop === null) return plottable
  const kept = new Set([
    ...plottable.slice(0, radarTop).map((opportunity) => opportunity.id),
    ...(hasFilters(query) ? visible.map((opportunity) => opportunity.id) : []),
    ...query.highlight,
    ...(query.selected ? [query.selected] : []),
  ])
  return plottable.filter((opportunity) => kept.has(opportunity.id))
}

// D6 del plan fe-radar-agent: con resaltados se ilumina lo resaltado aunque un filtro lo deje
// fuera (el agente resalta lo que va a explicar); sin resaltados, lo que entra en el filtro. La
// selección nunca se atenúa.
function collectDimmedIds(
  plotted: PlottedOpportunity[],
  visible: RankedOpportunity[],
  { highlight, selectedId }: { highlight: string[]; selectedId: string | undefined },
): Set<string> {
  const visibleIds = new Set(visible.map((opportunity) => opportunity.id))
  const isLit = (id: string) => (highlight.length > 0 ? highlight.includes(id) : visibleIds.has(id))
  const dimmed = plotted
    .map((opportunity) => opportunity.id)
    .filter((id) => id !== selectedId && !isLit(id))
  return new Set(dimmed)
}

const isPublishNow = (opportunity: Opportunity) => opportunity.recommendation === 'publish_now'

const countStage = (topics: Opportunity[], lifecycle: Lifecycle) =>
  topics.filter((opportunity) => opportunity.lifecycle === lifecycle).length

function countAll(ranked: RankedOpportunity[]): RadarView['counts'] {
  return {
    publishNow: ranked.filter(isPublishNow).length,
    accelerating: countStage(ranked, 'accelerating'),
    emerging: countStage(ranked, 'emerging'),
    unknown: countStage(ranked, 'unknown'),
  }
}

interface CounterFilterState {
  lifecycle: Lifecycle[]
  recommendation: Recommendation | null
}

const COUNTER_FILTER: Record<CounterFilter, CounterFilterState> = {
  publish_now: { lifecycle: [], recommendation: 'publish_now' },
  accelerating: { lifecycle: ['accelerating'], recommendation: null },
  emerging: { lifecycle: ['emerging'], recommendation: null },
  unknown: { lifecycle: ['unknown'], recommendation: null },
}

function sameStages(a: Lifecycle[], b: Lifecycle[]): boolean {
  return a.length === b.length && a.every((stage) => b.includes(stage))
}

// D2: un contador está pulsado solo si los filtros son exactamente los suyos; si el agente o la
// URL ponen otra combinación (varias etapas, `gap`, confianza o tema), no hay ninguno pulsado.
export function activeCounterOf(query: RadarQuery): CounterFilter | null {
  if (query.gap || query.confidence !== null || query.topic !== null) return null
  const isActive = (counter: CounterFilter) => {
    const { lifecycle, recommendation } = COUNTER_FILTER[counter]
    return query.recommendation === recommendation && sameStages(query.lifecycle, lifecycle)
  }
  return COUNTER_FILTERS.find(isActive) ?? null
}

// D2: selección única. Pulsar un contador sustituye cualquier otro filtro; pulsar el activo lo
// quita.
export function counterPatch(counter: CounterFilter, query: RadarQuery): Partial<RadarQuery> {
  if (activeCounterOf(query) === counter) return resetViewPatch()
  return { ...resetViewPatch(), ...COUNTER_FILTER[counter] }
}

const FALLBACK_PICKS = 3

function pickWeek(ranked: RankedOpportunity[]): WeekPicks {
  const publishNow = ranked.filter(isPublishNow)
  if (publishNow.length > 0) return { topics: publishNow, hasPublishNow: true }
  return { topics: ranked.slice(0, FALLBACK_PICKS), hasPublishNow: false }
}

function sumOutliers(ranked: RankedOpportunity[]): number {
  return ranked.reduce((sum, opportunity) => sum + opportunity.outlier_count, 0)
}

export function buildRadarView(
  list: OpportunityList | null,
  query: RadarQuery,
  { radarTop = RADAR_TOP }: RadarOptions = {},
): RadarView {
  const ranked = rankInApiOrder(list)
  const visible = ranked
    .filter((opportunity) => matchesFilters(opportunity, query))
    .sort(RANKING_ORDER[query.sort])
  const plotted = pickPlotted(ranked, visible, query, radarTop)
  const plottableCount = ranked.filter(hasAudienceFit).length
  // D7: sin `?selected=` válido no hay tema seleccionado.
  const selected = ranked.find((opportunity) => opportunity.id === query.selected) ?? null
  return {
    total: ranked.length,
    ranked,
    visible,
    isFiltered: hasFilters(query),
    plotted,
    plottableCount,
    unevaluatedCount: ranked.length - plottableCount,
    dimmedIds: collectDimmedIds(plotted, visible, {
      highlight: query.highlight,
      selectedId: selected?.id,
    }),
    selected,
    counts: countAll(ranked),
    activeCounter: activeCounterOf(query),
    weekPicks: pickWeek(ranked),
    outlierPieces: sumOutliers(ranked),
  }
}

const STAGE_SEPARATOR = ' o '
const FILTER_SEPARATOR = ' · '

function topicsLabel(count: number): string {
  return countLabel(count, 'tema', 'temas')
}

// No "con datos suficientes": la cuenta incluye temas preliminares (D14 del plan fe-radar-view).
function analyzedTopicsLabel(count: number): string {
  return countLabel(count, 'tema analizado', 'temas analizados')
}

function stageLabel(lifecycle: Lifecycle): string {
  return LIFECYCLE_STYLE[lifecycle].label.toLowerCase()
}

function describeFilters(query: RadarQuery): string {
  const parts: string[] = []
  if (query.lifecycle.length > 0) {
    parts.push(`etapa ${query.lifecycle.map(stageLabel).join(STAGE_SEPARATOR)}`)
  }
  if (query.recommendation) {
    parts.push(`para ${RECOMMENDATION_LABEL[query.recommendation].toLowerCase()}`)
  }
  if (query.gap) parts.push('con hueco en LATAM')
  if (query.confidence) parts.push(`confianza ${CONFIDENCE_LABEL[query.confidence]}`)
  if (query.topic) parts.push(`tema «${query.topic}»`)
  return parts.join(FILTER_SEPARATOR)
}

export function radarHeadline(view: RadarView, query: RadarQuery): string {
  if (hasFilters(query)) return `${view.visible.length} de ${topicsLabel(view.total)}`
  return `${topicsLabel(view.total)} esta semana`
}

// El agente puede ordenar por aceleración (`sort` en la URL) aunque no haya botón de orden.
const SORT_PHRASE: Record<RadarQuery['sort'], string> = {
  opportunity: 'Ordenados por oportunidad.',
  acceleration: 'Ordenados por aceleración.',
}
const HOW_TO_SELECT = 'Elige un tema en el radar o en el ranking para verlo al lado.'

function howToRead(query: RadarQuery): string {
  return `${SORT_PHRASE[query.sort]} ${HOW_TO_SELECT}`
}

export function radarSubline(view: RadarView, query: RadarQuery): string {
  if (hasFilters(query)) {
    return `Filtro: ${describeFilters(query)}. El resto queda atenuado en el radar.`
  }
  if (view.total < EXPECTED_OPPORTUNITIES) {
    return `Hay ${analyzedTopicsLabel(view.total)} esta semana. ${howToRead(query)}`
  }
  return howToRead(query)
}

function missingStageReason(unknownCount: number, preliminaryCount: number): string {
  const unmatchedCount = unknownCount - preliminaryCount
  if (preliminaryCount === 0) return 'ninguna regla se cumple'
  if (unmatchedCount === 0) return 'por falta de datos'
  return `${preliminaryCount} por falta de datos y ${unmatchedCount} porque ninguna regla se cumple`
}

// D4 del plan fe-dashboard-v2: `preliminary` = datos insuficientes (CLAUDE.md §7); el resto de
// los temas sin etapa tiene datos, pero ninguna regla se cumple.
export function describeStageUnknowns(
  topics: readonly Opportunity[],
  monitoringStartedAt: string,
): string {
  const since = `Datos desde el ${formatUtcTimestamp(monitoringStartedAt)}.`
  const unknown = topics.filter((opportunity) => opportunity.lifecycle === 'unknown')
  if (unknown.length === 0) return `Todos los temas tienen una tendencia clara. ${since}`
  const preliminaryCount = unknown.filter(
    (opportunity) => opportunity.growth_status === 'preliminary',
  ).length
  const verb = unknown.length === 1 ? 'tiene' : 'tienen'
  const share = `${unknown.length} de ${topicsLabel(topics.length)}`
  return `${share} no ${verb} una tendencia clara: ${missingStageReason(unknown.length, preliminaryCount)}. ${since}`
}
