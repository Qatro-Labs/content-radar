import type { LocationQuery } from 'vue-router'

import type { components } from '@/types/api'

import { countLabel, EVIDENCE_LIMIT, formatCount } from './evidenceFormat'
import { formatUtcDay } from './format'

type Schemas = components['schemas']
type Evidence = Schemas['Evidence']
type Opportunity = Schemas['Opportunity']

export const EXPLORE_FILTERS = ['outliers', 'youtube', 'hackernews'] as const
export type ExploreFilter = (typeof EXPLORE_FILTERS)[number]
export const EXPLORE_FILTER_PARAM = 'filter'

// "Dónde está funcionando" muestra los cinco primeros temas y fuentes.
const TOP_LIMIT = 5

// Una URL puede estar en la evidencia de varios temas: cada pieza se atribuye a uno solo.
export type Piece = Evidence & { opportunity: Opportunity; rank: number }

export interface ExploreCounts {
  total: number
  outliers: number
  youtube: number
  hackernews: number
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
  loadedTopicCount: number
  isCapped: boolean
  topTopics: Opportunity[]
  topSources: SourceOutliers[]
}

export interface ExploreInput {
  // En el orden de la API, que es el del ranking.
  opportunities: readonly Opportunity[]
  // Solo los temas cuya evidencia ya cargó.
  evidenceById: ReadonlyMap<string, readonly Evidence[]>
  filter: ExploreFilter | null
  text: string
}

export function parseExploreFilter(query: LocationQuery): ExploreFilter | null {
  const raw = query[EXPLORE_FILTER_PARAM]
  const value = Array.isArray(raw) ? raw[0] : raw
  return EXPLORE_FILTERS.find((filter) => filter === value) ?? null
}

// `is_outlier` lo decide la API (≥ 3×, CLAUDE.md §7): el front no recalcula el umbral.
const FILTER_MATCHES: Record<ExploreFilter, (piece: Evidence) => boolean> = {
  outliers: (piece) => piece.is_outlier === true,
  youtube: (piece) => piece.platform === 'youtube',
  hackernews: (piece) => piece.platform === 'hackernews',
}

// NFD separa la tilde de su letra ("á" → "a" + U+0301); quitar las marcas deja "a".
const COMBINING_MARKS = /\p{M}/gu

function foldForSearch(text: string): string {
  return text.normalize('NFD').replace(COMBINING_MARKS, '').toLocaleLowerCase('es')
}

// La misma URL puede estar en la evidencia de dos temas: se queda con el de mejor puesto, que es
// el primero que se recorre.
function collectPieces({ opportunities, evidenceById }: ExploreInput): Piece[] {
  const byUrl = new Map<string, Piece>()
  opportunities.forEach((opportunity, index) => {
    for (const evidence of evidenceById.get(opportunity.id) ?? []) {
      if (byUrl.has(evidence.url)) continue
      byUrl.set(evidence.url, { ...evidence, opportunity, rank: index + 1 })
    }
  })
  return [...byUrl.values()]
}

// Sin ratio no hay rendimiento que comparar: esas piezas van al final, nunca como si fueran 0.
function compareRatios(a: Piece, b: Piece): number {
  const ratioA = a.outlier_ratio ?? null
  const ratioB = b.outlier_ratio ?? null
  if (ratioA !== null && ratioB !== null) return ratioB - ratioA
  if (ratioA === ratioB) return 0
  return ratioA === null ? 1 : -1
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

function countByKind(pieces: Piece[]): ExploreCounts {
  return {
    total: pieces.length,
    outliers: countPieces(pieces, FILTER_MATCHES.outliers),
    youtube: countPieces(pieces, FILTER_MATCHES.youtube),
    hackernews: countPieces(pieces, FILTER_MATCHES.hackernews),
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
  for (const piece of pieces.filter(FILTER_MATCHES.outliers)) {
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
  const filterMatches = filter === null ? null : FILTER_MATCHES[filter]
  return pieces.filter(
    (piece) => (filterMatches === null || filterMatches(piece)) && matchesText(piece, foldedText),
  )
}

function loadedEvidenceLists({
  opportunities,
  evidenceById,
}: ExploreInput): (readonly Evidence[])[] {
  return opportunities.flatMap((opportunity) => {
    const list = evidenceById.get(opportunity.id)
    return list === undefined ? [] : [list]
  })
}

export function buildExploreView(input: ExploreInput): ExploreViewModel {
  const pieces = collectPieces(input).sort(byRatioThenRecency)
  const loadedLists = loadedEvidenceLists(input)
  return {
    pieces,
    visible: filterPieces(pieces, input),
    counts: countByKind(pieces),
    publishedRange: publishedRangeOf(pieces),
    loadedTopicCount: loadedLists.length,
    isCapped: loadedLists.some((list) => list.length >= EVIDENCE_LIMIT),
    topTopics: topicsWithMostOutliers(input.opportunities),
    topSources: sourcesWithMostOutliers(pieces),
  }
}

export type ExploreSummaryInput = Pick<
  ExploreViewModel,
  'counts' | 'loadedTopicCount' | 'publishedRange' | 'isCapped'
>

function describePublished(range: PublishedRange | null, total: number): string {
  if (range === null) return ''
  const published = total === 1 ? 'publicada' : 'publicadas'
  if (range.from === range.to) return `, ${published} el ${range.from}`
  return `, ${published} entre el ${range.from} y el ${range.to}`
}

export function exploreSummary(input: ExploreSummaryInput): string {
  const { counts, loadedTopicCount, publishedRange, isCapped } = input
  const pieces = countLabel(counts.total, 'pieza', 'piezas')
  const topics = loadedTopicCount === 1 ? '1 tema' : `los ${formatCount(loadedTopicCount)} temas`
  const outliers = countLabel(counts.outliers, 'rinde', 'rinden')
  const cap = isCapped ? ` Hasta ${EVIDENCE_LIMIT} piezas por tema.` : ''
  return (
    `${pieces} de ${topics}${describePublished(publishedRange, counts.total)}. ` +
    `${outliers} 3× o más que su canal.${cap}`
  )
}
