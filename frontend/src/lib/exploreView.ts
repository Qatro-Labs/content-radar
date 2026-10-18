import type { LocationQuery } from 'vue-router'

import type { components } from '@/types/api'

import { compareRatios, countLabel, EVIDENCE_LIMIT, formatCount } from './evidenceFormat'
import { formatUtcDay } from './format'

type Schemas = components['schemas']
type Evidence = Schemas['Evidence']
type TopicEvidence = Schemas['TopicEvidence']
type Opportunity = Schemas['Opportunity']
type Platform = Schemas['Platform']

// Las plataformas con métricas públicas, que son las que tiene sentido filtrar por rendimiento.
// RSS no publica métricas; Brave solo guarda agregados y LinkedIn no entra en el MVP.
export const FILTERABLE_PLATFORMS = [
  'youtube',
  'hackernews',
  'tiktok',
  'reddit',
  'instagram',
  'x',
] as const satisfies readonly Platform[]
export type FilterablePlatform = (typeof FILTERABLE_PLATFORMS)[number]

export const EXPLORE_FILTERS = ['outliers', ...FILTERABLE_PLATFORMS] as const
export type ExploreFilter = (typeof EXPLORE_FILTERS)[number]
export const EXPLORE_FILTER_PARAM = 'filter'
// El texto va en la URL para que la paleta ⌘K pueda abrir Explorar con una fuente ya filtrada.
export const EXPLORE_TEXT_PARAM = 'q'

// "Dónde está funcionando" muestra los cinco primeros temas y fuentes.
const TOP_LIMIT = 5

// Una URL puede estar en la evidencia de varios temas: cada pieza se atribuye a uno solo.
export type Piece = Evidence & { opportunity: Opportunity; rank: number }

export interface PlatformCount {
  platform: FilterablePlatform
  count: number
}

export interface ExploreCounts {
  total: number
  outliers: number
  // Solo las plataformas con piezas, de más a menos: una sin piezas no tiene baldosa.
  platforms: PlatformCount[]
  rss: number
}

export interface PublishedRange {
  from: string
  to: string
}

export interface SourceOutliers {
  source: string
  count: number
  share: number
}

export interface ExploreViewModel {
  pieces: Piece[]
  visible: Piece[]
  counts: ExploreCounts
  publishedRange: PublishedRange | null
  // Temas del ranking con alguna pieza en la evidencia servida.
  topicsWithPiecesCount: number
  isCapped: boolean
  topTopics: Opportunity[]
  topSources: SourceOutliers[]
}

export interface LoadedEvidence {
  // En el orden de la API, que es el del ranking.
  opportunities: readonly Opportunity[]
  // GET /evidence: las piezas de todos los temas, cada una con su `opportunity_id`.
  evidence: readonly TopicEvidence[]
}

interface TopicPieces {
  opportunity: Opportunity
  rank: number
  pieces: readonly TopicEvidence[]
}

export interface ExploreInput extends LoadedEvidence {
  filter: ExploreFilter | null
  text: string
}

export function parseExploreFilter(query: LocationQuery): ExploreFilter | null {
  const raw = query[EXPLORE_FILTER_PARAM]
  const value = Array.isArray(raw) ? raw[0] : raw
  return EXPLORE_FILTERS.find((filter) => filter === value) ?? null
}

export function parseExploreText(query: LocationQuery): string {
  const raw = query[EXPLORE_TEXT_PARAM]
  const value = Array.isArray(raw) ? raw[0] : raw
  return value ?? ''
}

// `is_outlier` lo decide la API (≥ 3×, CLAUDE.md §7): el front no recalcula el umbral.
function matchesFilter(filter: ExploreFilter, piece: Evidence): boolean {
  return filter === 'outliers' ? piece.is_outlier === true : piece.platform === filter
}

// NFD separa la tilde de su letra ("á" → "a" + U+0301); quitar las marcas deja "a".
const COMBINING_MARKS = /\p{M}/gu

export function foldForSearch(text: string): string {
  return text.normalize('NFD').replace(COMBINING_MARKS, '').toLocaleLowerCase('es')
}

function groupByOpportunity(evidence: readonly TopicEvidence[]): Map<string, TopicEvidence[]> {
  const groups = new Map<string, TopicEvidence[]>()
  for (const piece of evidence) {
    const group = groups.get(piece.opportunity_id)
    if (group === undefined) groups.set(piece.opportunity_id, [piece])
    else group.push(piece)
  }
  return groups
}

// En el orden del ranking. Una pieza de un tema que no está en la lista se descarta: no hay tema
// al que atribuirla.
function piecesByTopic({ opportunities, evidence }: LoadedEvidence): TopicPieces[] {
  const groups = groupByOpportunity(evidence)
  return opportunities.flatMap((opportunity, index) => {
    const pieces = groups.get(opportunity.id)
    return pieces === undefined ? [] : [{ opportunity, rank: index + 1, pieces }]
  })
}

// La misma URL puede estar en la evidencia de dos temas: se queda con el de mejor puesto, que es
// el primero que se recorre.
function uniquePieces(topics: readonly TopicPieces[]): Piece[] {
  const byUrl = new Map<string, Piece>()
  for (const { opportunity, rank, pieces } of topics) {
    for (const piece of pieces) {
      if (!byUrl.has(piece.url)) byUrl.set(piece.url, { ...piece, opportunity, rank })
    }
  }
  return [...byUrl.values()]
}

export function collectPieces(loaded: LoadedEvidence): Piece[] {
  return uniquePieces(piecesByTopic(loaded))
}

function byRatioThenRecency(a: Piece, b: Piece): number {
  return compareRatios(a, b) || Date.parse(b.published_at) - Date.parse(a.published_at)
}

function matchesText(piece: Piece, foldedText: string): boolean {
  if (foldedText === '') return true
  return [piece.title, piece.source].some((field) => foldForSearch(field).includes(foldedText))
}

function countPieces(pieces: Piece[], matches: (piece: Piece) => boolean): number {
  return pieces.filter(matches).length
}

// `sort` es estable: a igualdad de piezas, las plataformas conservan el orden de la lista.
function countByPlatform(pieces: Piece[]): PlatformCount[] {
  return FILTERABLE_PLATFORMS.map((platform) => ({
    platform,
    count: countPieces(pieces, (piece) => piece.platform === platform),
  }))
    .filter((entry) => entry.count > 0)
    .sort((a, b) => b.count - a.count)
}

function countByKind(pieces: Piece[]): ExploreCounts {
  return {
    total: pieces.length,
    outliers: countPieces(pieces, (piece) => matchesFilter('outliers', piece)),
    platforms: countByPlatform(pieces),
    rss: countPieces(pieces, (piece) => piece.platform === 'rss'),
  }
}

function publishedRangeOf(pieces: Piece[]): PublishedRange | null {
  const dates = pieces.map((piece) => piece.published_at)
  dates.sort((a, b) => Date.parse(a) - Date.parse(b))
  const first = dates.at(0)
  const last = dates.at(-1)
  if (first === undefined || last === undefined) return null
  return { from: formatUtcDay(first), to: formatUtcDay(last) }
}

// `sort` es estable: a igualdad de outliers, los temas conservan el orden del ranking.
function topicsWithMostOutliers(opportunities: readonly Opportunity[]): Opportunity[] {
  return opportunities
    .filter((opportunity) => opportunity.outlier_count > 0)
    .sort((a, b) => b.outlier_count - a.outlier_count)
    .slice(0, TOP_LIMIT)
}

function sourcesWithMostOutliers(pieces: Piece[]): SourceOutliers[] {
  const counts = new Map<string, number>()
  for (const piece of pieces.filter((item) => matchesFilter('outliers', item))) {
    counts.set(piece.source, (counts.get(piece.source) ?? 0) + 1)
  }
  const top = [...counts]
    .map(([source, count]) => ({ source, count }))
    .sort((a, b) => b.count - a.count || a.source.localeCompare(b.source, 'es'))
    .slice(0, TOP_LIMIT)
  const max = top[0]?.count ?? 0
  return top.map((entry) => ({ ...entry, share: entry.count / max }))
}

function filterPieces(pieces: Piece[], { filter, text }: ExploreInput): Piece[] {
  const foldedText = foldForSearch(text.trim())
  return pieces.filter(
    (piece) => (filter === null || matchesFilter(filter, piece)) && matchesText(piece, foldedText),
  )
}

export function buildExploreView(input: ExploreInput): ExploreViewModel {
  const topics = piecesByTopic(input)
  const pieces = uniquePieces(topics).sort(byRatioThenRecency)
  return {
    pieces,
    visible: filterPieces(pieces, input),
    counts: countByKind(pieces),
    publishedRange: publishedRangeOf(pieces),
    topicsWithPiecesCount: topics.length,
    isCapped: topics.some((topic) => topic.pieces.length >= EVIDENCE_LIMIT),
    topTopics: topicsWithMostOutliers(input.opportunities),
    topSources: sourcesWithMostOutliers(pieces),
  }
}

export type ExploreSummaryInput = Pick<
  ExploreViewModel,
  'counts' | 'topicsWithPiecesCount' | 'publishedRange' | 'isCapped'
>

function describePublished(range: PublishedRange | null, total: number): string {
  if (range === null) return ''
  const published = total === 1 ? 'publicada' : 'publicadas'
  if (range.from === range.to) return `, ${published} el ${range.from}`
  return `, ${published} entre el ${range.from} y el ${range.to}`
}

export function exploreSummary(input: ExploreSummaryInput): string {
  const { counts, topicsWithPiecesCount, publishedRange, isCapped } = input
  const pieces = countLabel(counts.total, 'pieza', 'piezas')
  const topics =
    topicsWithPiecesCount === 1 ? '1 tema' : `los ${formatCount(topicsWithPiecesCount)} temas`
  const rinden = counts.outliers === 1 ? 'rinde' : 'rinden'
  const cap = isCapped ? ` (hasta ${EVIDENCE_LIMIT} por tema)` : ''
  return (
    `${formatCount(counts.outliers)} ${rinden} 3× o más que lo normal en su canal. ` +
    `${pieces} de ${topics}${cap}${describePublished(publishedRange, counts.total)}.`
  )
}
