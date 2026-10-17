import type { components } from '@/types/api'

import { countLabel, PLATFORM_LABEL, shortSourceName } from './evidenceFormat'
import { formatUtcDay, formatUtcTime, formatUtcTimestamp } from './format'
import {
  CONFIDENCE_LABEL,
  formatFit,
  formatScore,
  formatShare,
  GROWTH_LABEL,
  latamGapLabel,
} from './opportunityFormat'

type Schemas = components['schemas']
type Opportunity = Schemas['Opportunity']
type OpportunityList = Schemas['OpportunityList']
type OpportunityTimeline = Schemas['OpportunityTimeline']
type TimelinePoint = Schemas['TimelinePoint']
type ScoreBreakdown = Schemas['ScoreBreakdown']
type ScoreComponentName = Schemas['ScoreComponentName']
type ScorePenalty = Schemas['ScorePenalty']
type ScorePenaltyName = Schemas['ScorePenaltyName']
type FitCriterion = Schemas['FitCriterion']
type AudienceFitCriterion = Schemas['AudienceFitCriterion']
type Evidence = Schemas['Evidence']
type Platform = Schemas['Platform']

// DESIGN.md §9: el signo menos tipográfico (U+2212), no el guion.
const MINUS_SIGN = '−'
const RANGE_DASH = '–'
const LIST_SEPARATOR = ' · '

export function dossierStatusLine(opportunity: Opportunity): string {
  return [
    GROWTH_LABEL[opportunity.growth_status],
    `confianza ${CONFIDENCE_LABEL[opportunity.confidence]}`,
    countLabel(opportunity.source_count, 'fuente independiente', 'fuentes independientes'),
    latamGapLabel(opportunity.latam_gap),
    `actualizado el ${formatUtcTimestamp(opportunity.last_updated)}`,
  ].join(LIST_SEPARATOR)
}

export interface TopicRank {
  rank: number
  total: number
}

// El puesto es el orden en que llega la lista: el backend ya ordena por su ranking.
export function rankOf(list: OpportunityList | null | undefined, id: string): TopicRank | null {
  if (list == null) return null
  const index = list.items.findIndex((item) => item.id === id)
  return index < 0 ? null : { rank: index + 1, total: list.items.length }
}

// Un tema que ya no está en la lista servida no tiene puesto: se dice, no se inventa.
export function rankLabel(rank: TopicRank | null): string {
  return rank === null ? 'puesto no disponible' : `puesto ${rank.rank} de ${rank.total}`
}

export interface TimelineBar {
  date: string
  label: string
  count: number
}

export interface TimelineWindows {
  previous: TimelineBar[]
  current: TimelineBar[]
  previousLabel: string
  currentLabel: string
  scaleMax: number
  cutoffTime: string
}

const utcDayOfMonth = new Intl.DateTimeFormat('es-ES', { timeZone: 'UTC', day: '2-digit' })

function toBar(point: TimelinePoint): TimelineBar {
  return { date: point.date, label: formatUtcDay(point.date), count: point.count }
}

// "12–14/10"; si la ventana cruza de mes, "30/09–02/10".
function windowRange(bars: TimelineBar[]): string {
  const first = bars.at(0)
  const last = bars.at(-1)
  if (first === undefined || last === undefined) return ''
  const sameMonth = new Date(first.date).getUTCMonth() === new Date(last.date).getUTCMonth()
  const start = sameMonth ? utcDayOfMonth.format(new Date(first.date)) : first.label
  return `${start}${RANGE_DASH}${last.label}`
}

function windowLabel(name: string, bars: TimelineBar[]): string {
  const range = windowRange(bars)
  return range === '' ? name : `${name}${LIST_SEPARATOR}${range}`
}

// Los puntos de /timeline son periodos de 24 h que terminan a la hora de `last_updated`, no días
// de calendario (DESIGN.md §8): por eso la hora de corte viaja con las ventanas.
export function splitTimeline(timeline: OpportunityTimeline, lastUpdated: string): TimelineWindows {
  const bars = (window: TimelinePoint['window']) =>
    timeline.points.filter((point) => point.window === window).map(toBar)
  const previous = bars('previous')
  const current = bars('current')
  return {
    previous,
    current,
    previousLabel: windowLabel('Ventana anterior', previous),
    currentLabel: windowLabel('Ventana actual', current),
    // Con todo a 0 la escala sigue siendo 1: dividir entre 0 no dibuja nada legible.
    scaleMax: Math.max(1, ...timeline.points.map((point) => point.count)),
    cutoffTime: formatUtcTime(lastUpdated),
  }
}

export const COMPONENT_LABEL: Record<ScoreComponentName, string> = {
  momentum: 'Momentum',
  audience_fit: 'Encaje con 30X',
  cross_source: 'Fuentes independientes',
  freshness: 'Frescura',
  actionability: 'Accionabilidad',
}

export interface ComponentRow {
  name: ScoreComponentName
  label: string
  value: number
  display: string
  weightLabel: string
}

// El encaje se escribe con su banda ("Alto · 83"), como en el resto de la UI (DESIGN.md §9).
export function componentRows(breakdown: ScoreBreakdown): ComponentRow[] {
  return breakdown.components.map(({ name, value, weight }) => ({
    name,
    label: COMPONENT_LABEL[name],
    value,
    display: name === 'audience_fit' ? formatFit(value) : formatScore(value),
    weightLabel: `peso ${formatShare(weight)}`,
  }))
}

export const PENALTY_LABEL: Record<ScorePenaltyName, string> = {
  single_source: 'Una sola fuente',
  small_sample: 'Muestra pequeña',
}

export function describePenalties(penalties: readonly ScorePenalty[]): string {
  if (penalties.length === 0) return 'sin penalizaciones'
  return penalties
    .map(({ name, points }) => `${PENALTY_LABEL[name]} ${MINUS_SIGN}${formatScore(points)}`)
    .join(LIST_SEPARATOR)
}

// "Oportunidad · puesto 3 de 38 · sin penalizaciones". Sin `rankText` (la lista aún no llegó) se
// omite el puesto; sin desglose no hay penalizaciones que contar.
export function compositionSubline(
  rankText: string | null,
  breakdown: ScoreBreakdown | null,
): string {
  const parts = ['Oportunidad']
  if (rankText !== null) parts.push(rankText)
  if (breakdown !== null) parts.push(describePenalties(breakdown.penalties))
  return parts.join(LIST_SEPARATOR)
}

export const CRITERION_LABEL: Record<FitCriterion, string> = {
  business_impact: 'Impacto en decisiones empresariales',
  org_application: 'Aplicación real en organizaciones',
  exec_readability: 'Comprensible para directivos no técnicos',
  latam_relevance: 'Relevancia para LATAM',
  pillar_fit: 'Encaje con los pilares de 30X',
  actionable_content: 'Convertible en contenido accionable',
}

export interface CitationChip {
  url: string
  label: string
  isInEvidence: boolean
}

// La URL viene del LLM: si no se puede leer, se muestra tal cual en lugar de romper la vista.
function hostOf(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

// D11: un chip por pieza citada. La evidencia servida tiene como mucho 25 piezas, así que una
// cita puede no estar en la lista: entonces se nombra por su host y no se puede resaltar.
export function citationChips(
  criterion: AudienceFitCriterion,
  evidence: readonly Evidence[],
): CitationChip[] {
  return criterion.evidence_urls.map((url) => {
    const piece = evidence.find((item) => item.url === url)
    return {
      url,
      label: piece ? shortSourceName(piece.source) : hostOf(url),
      isInEvidence: piece !== undefined,
    }
  })
}

export const ALL_PLATFORMS = 'all'
export type PlatformFilter = Platform | typeof ALL_PLATFORMS

export interface PlatformCount {
  platform: PlatformFilter
  label: string
  count: number
}

// Orden fijo del contrato (YouTube, Hacker News, RSS…), no el de aparición en la evidencia.
const PLATFORM_ORDER = Object.keys(PLATFORM_LABEL) as Platform[]

export function platformCounts(evidence: readonly Evidence[]): PlatformCount[] {
  const present = PLATFORM_ORDER.flatMap((platform) => {
    const count = evidence.filter((item) => item.platform === platform).length
    return count === 0 ? [] : [{ platform, label: PLATFORM_LABEL[platform], count }]
  })
  return [{ platform: ALL_PLATFORMS, label: 'Todas', count: evidence.length }, ...present]
}

export function filterByPlatform(
  evidence: readonly Evidence[],
  filter: PlatformFilter,
): Evidence[] {
  if (filter === ALL_PLATFORMS) return [...evidence]
  return evidence.filter((item) => item.platform === filter)
}

// GET /evidence devuelve como mucho 25 piezas por tema: con 25, puede haber más que no se ven.
export const EVIDENCE_LIMIT = 25

// D11: con una pieza citada, esa se marca y el resto baja de opacidad sin desaparecer.
export type RowEmphasis = 'cited' | 'dimmed' | 'none'

export function rowEmphasis(url: string, citedUrl: string | null): RowEmphasis {
  if (citedUrl === null) return 'none'
  return url === citedUrl ? 'cited' : 'dimmed'
}
