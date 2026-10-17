import type { components } from '@/types/api'

import { collectPieces, foldForSearch, type LoadedEvidence, type Piece } from './exploreView'

type Opportunity = components['schemas']['Opportunity']

// La paleta sirve para saltar, no para leer: con más filas por grupo, el siguiente grupo queda
// fuera de la vista.
export const MAX_RESULTS_PER_GROUP = 8

export interface SourceResult {
  source: string
  pieceCount: number
}

export interface SearchResults {
  topics: Opportunity[]
  pieces: Piece[]
  sources: SourceResult[]
}

export interface SearchInput extends LoadedEvidence {
  text: string
}

function piecesPerSource(pieces: Piece[]): SourceResult[] {
  const counts = new Map<string, number>()
  for (const piece of pieces) counts.set(piece.source, (counts.get(piece.source) ?? 0) + 1)
  return [...counts]
    .map(([source, pieceCount]) => ({ source, pieceCount }))
    .sort((a, b) => b.pieceCount - a.pieceCount || a.source.localeCompare(b.source, 'es'))
}

function firstMatches<T>(
  items: readonly T[],
  searchableFields: (item: T) => string[],
  foldedText: string,
): T[] {
  return items
    .filter((item) =>
      searchableFields(item).some((field) => foldForSearch(field).includes(foldedText)),
    )
    .slice(0, MAX_RESULTS_PER_GROUP)
}

// Temas en el orden del ranking; piezas sin repetir y atribuidas al tema de mejor puesto, como en
// Explorar. Sin texto, cada grupo muestra sus primeros resultados.
export function buildSearchResults({ text, ...loaded }: SearchInput): SearchResults {
  const foldedText = foldForSearch(text.trim())
  const pieces = collectPieces(loaded)
  return {
    topics: firstMatches(loaded.opportunities, (topic) => [topic.topic], foldedText),
    pieces: firstMatches(pieces, (piece) => [piece.title, piece.source], foldedText),
    sources: firstMatches(piecesPerSource(pieces), (entry) => [entry.source], foldedText),
  }
}

export function hasResults({ topics, pieces, sources }: SearchResults): boolean {
  return topics.length + pieces.length + sources.length > 0
}
