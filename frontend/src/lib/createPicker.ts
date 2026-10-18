import type { components } from '@/types/api'

import { countLabel, EVIDENCE_LIMIT, formatCount } from './evidenceFormat'
import { foldForSearch } from './exploreView'
import {
  formatAcceleration,
  formatScore,
  GROWTH_LABEL,
  isDeclining,
  SCORE_MAX,
} from './opportunityFormat'

type Schemas = components['schemas']
type Opportunity = Schemas['Opportunity']

// Artboard A de Crear: sin búsqueda, la lista enseña los primeros del ranking y el resto se
// despliega; con todos a la vista, la lista empuja el destacado fuera de la pantalla.
export const COLLAPSED_TOPICS = 7

export interface TopicSplit {
  featured: Opportunity[]
  others: Opportunity[]
}

// Los dos grupos conservan el orden del ranking de la API.
export function splitByPublishNow(items: readonly Opportunity[]): TopicSplit {
  return {
    featured: items.filter((item) => item.recommendation === 'publish_now'),
    others: items.filter((item) => item.recommendation !== 'publish_now'),
  }
}

export function featuredNote(count: number): string {
  if (count === 1) return 'El único tema en «Publicar ya» esta semana'
  return `${formatCount(count)} temas en «Publicar ya»`
}

// Sin «Por qué importa» se cuenta la regla de la recomendación; sin ninguno, no se escribe nada
// (CLAUDE.md §2.3).
export function featuredSummary(
  opportunity: Pick<Opportunity, 'why_it_matters' | 'recommendation_reason'>,
): string | null {
  return opportunity.why_it_matters.trim() || opportunity.recommendation_reason?.trim() || null
}

export interface FeaturedTile {
  label: string
  value: string
  isMissing: boolean
  isNegative: boolean
}

export function featuredTiles(opportunity: Opportunity): FeaturedTile[] {
  const score = opportunity.opportunity_score ?? null
  return [
    {
      // "de 100" solo acompaña a una cifra: junto a "no disponible" no dice nada.
      label: score === null ? 'Oportunidad' : `Oportunidad de ${SCORE_MAX}`,
      value: formatScore(score),
      isMissing: score === null,
      isNegative: false,
    },
    {
      // CLAUDE.md §2.5: el tipo de evidencia va siempre junto a la aceleración.
      label: `Aceleración · ${GROWTH_LABEL[opportunity.growth_status]}`,
      value: formatAcceleration(opportunity.acceleration),
      isMissing: false,
      isNegative: isDeclining(opportunity.acceleration),
    },
    {
      label: 'Fuentes independientes',
      value: formatCount(opportunity.source_count),
      isMissing: false,
      isNegative: false,
    },
  ]
}

// La API devuelve hasta EVIDENCE_LIMIT piezas por tema: con el tope lleno puede haber más.
export function morePiecesLine(total: number, shown: number): string | null {
  const remaining = total - shown
  if (remaining <= 0) return null
  const atLeast = total >= EVIDENCE_LIMIT ? 'al menos ' : ''
  return `y ${atLeast}${countLabel(remaining, 'pieza', 'piezas')} más del tema`
}

export interface TopicListInput {
  topics: readonly Opportunity[]
  hasFeatured: boolean
  text: string
  expanded: boolean
}

export interface TopicListView {
  title: string
  countLine: string
  rows: Opportunity[]
  // `null` cuando no queda nada plegado.
  expandLabel: string | null
  noMatches: boolean
}

function restingCountLine(count: number, hasFeatured: boolean): string {
  if (!hasFeatured) {
    return 'Ningún tema está en «Publicar ya» esta semana: estos son todos, por oportunidad.'
  }
  const order =
    count === 1 ? '1 tema más' : `${formatCount(count)} temas más, ordenados por oportunidad`
  return `${order}. Cualquiera sirve: Rad avisa si conviene esperar.`
}

// Con búsqueda se ven todas las coincidencias; sin ella, los primeros del ranking hasta que se
// despliega el resto.
export function buildTopicList({
  topics,
  hasFeatured,
  text,
  expanded,
}: TopicListInput): TopicListView {
  const foldedText = foldForSearch(text.trim())
  const title = hasFeatured ? 'O escribe de otro tema' : 'Todos los temas'
  if (foldedText !== '') {
    const matches = topics.filter((topic) => foldForSearch(topic.topic).includes(foldedText))
    return {
      title,
      countLine: `${formatCount(matches.length)} de ${countLabel(topics.length, 'tema', 'temas')}`,
      rows: matches,
      expandLabel: null,
      noMatches: matches.length === 0,
    }
  }
  const isCollapsed = !expanded && topics.length > COLLAPSED_TOPICS
  return {
    title,
    countLine: restingCountLine(topics.length, hasFeatured),
    rows: isCollapsed ? topics.slice(0, COLLAPSED_TOPICS) : [...topics],
    expandLabel: isCollapsed ? `Ver los ${formatCount(topics.length)} temas` : null,
    noMatches: false,
  }
}
