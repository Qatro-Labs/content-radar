import type { LocationQuery } from 'vue-router'

import type { components } from '@/types/api'

import { citationChipsFor, type CitationChip } from './dossierView'
import { compareRatios, countLabel, formatRatio } from './evidenceFormat'

type Schemas = components['schemas']
type BriefPlatform = Schemas['BriefPlatform']
type BriefGoal = Schemas['BriefGoal']
type BriefFormat = Schemas['BriefFormat']
type BriefRequest = Schemas['BriefRequest']
type EditorialBrief = Schemas['EditorialBrief']
type Evidence = Schemas['Evidence']
type Recommendation = Schemas['Recommendation']

export const BRIEF_PLATFORMS = [
  'linkedin',
  'instagram',
  'youtube',
  'newsletter',
] as const satisfies readonly BriefPlatform[]
export const BRIEF_GOALS = [
  'educate',
  'spark_conversation',
  'generate_leads',
] as const satisfies readonly BriefGoal[]
export const BRIEF_FORMATS = [
  'post',
  'carousel',
  'short_video',
  'long_video',
  'article',
] as const satisfies readonly BriefFormat[]

export const BRIEF_PLATFORM_LABEL: Record<BriefPlatform, string> = {
  linkedin: 'LinkedIn',
  instagram: 'Instagram',
  youtube: 'YouTube',
  newsletter: 'Newsletter',
}
export const BRIEF_GOAL_LABEL: Record<BriefGoal, string> = {
  educate: 'Educar',
  spark_conversation: 'Conversación',
  generate_leads: 'Captar leads',
}
export const BRIEF_FORMAT_LABEL: Record<BriefFormat, string> = {
  post: 'Post',
  carousel: 'Carrusel',
  short_video: 'Vídeo corto',
  long_video: 'Vídeo largo',
  article: 'Artículo',
}

export const BRIEF_PARAM = {
  opportunity: 'opportunity',
  platform: 'platform',
  goal: 'goal',
  format: 'format',
} as const

export interface BriefOptions {
  platform: BriefPlatform
  goal: BriefGoal
  format: BriefFormat
}

// LinkedIn es el ejemplo del reto y educar es lo que más publica 30X.
export const DEFAULT_BRIEF_OPTIONS: BriefOptions = {
  platform: 'linkedin',
  goal: 'educate',
  format: 'post',
}

export interface BriefQuery {
  opportunityId: string | null
  options: BriefOptions
  // Con las cuatro en la URL, el enlace es de un brief concreto y la vista lo genera al abrirse
  // (la API lo devuelve cacheado). Con menos, solo preselecciona.
  isComplete: boolean
}

function first(query: LocationQuery, key: string): string | null {
  const raw = query[key]
  const value = Array.isArray(raw) ? raw[0] : raw
  return value ?? null
}

function pick<T extends string>(allowed: readonly T[], value: string | null): T | null {
  return allowed.find((option) => option === value) ?? null
}

export function parseBriefQuery(query: LocationQuery): BriefQuery {
  const opportunityId = first(query, BRIEF_PARAM.opportunity)
  const platform = pick(BRIEF_PLATFORMS, first(query, BRIEF_PARAM.platform))
  const goal = pick(BRIEF_GOALS, first(query, BRIEF_PARAM.goal))
  const format = pick(BRIEF_FORMATS, first(query, BRIEF_PARAM.format))
  return {
    opportunityId: opportunityId || null,
    options: {
      platform: platform ?? DEFAULT_BRIEF_OPTIONS.platform,
      goal: goal ?? DEFAULT_BRIEF_OPTIONS.goal,
      format: format ?? DEFAULT_BRIEF_OPTIONS.format,
    },
    isComplete: Boolean(opportunityId) && platform !== null && goal !== null && format !== null,
  }
}

export function serializeBriefQuery(request: BriefRequest): Record<string, string> {
  return {
    [BRIEF_PARAM.opportunity]: request.opportunity_id,
    [BRIEF_PARAM.platform]: request.platform,
    [BRIEF_PARAM.goal]: request.goal,
    [BRIEF_PARAM.format]: request.format,
  }
}

export function sameRequest(a: BriefRequest | undefined, b: BriefRequest): boolean {
  return (
    a !== undefined &&
    a.opportunity_id === b.opportunity_id &&
    a.platform === b.platform &&
    a.goal === b.goal &&
    a.format === b.format
  )
}

// La API puede pedirlo igual; la UI avisa de que la recomendación va en contra, no lo esconde.
const ADVISED_AGAINST: readonly Recommendation[] = ['wait_for_case', 'discard']

export function isAdvisedAgainst(recommendation: Recommendation): boolean {
  return ADVISED_AGAINST.includes(recommendation)
}

// Con qué se escribirá el brief: las piezas que mejor rinden frente a su canal, outliers primero.
const FEATURED_PIECES = 3

export function featuredPieces(evidence: readonly Evidence[]): Evidence[] {
  return [...evidence].sort(compareRatios).slice(0, FEATURED_PIECES)
}

export const HOOK_MISSING = 'Gancho no disponible: no superó la comprobación de evidencia.'
export const WHY_IT_FITS_MISSING = 'Encaje no disponible: no se pudo comprobar con la evidencia.'
export const NO_LIMITATIONS = 'No hay limitaciones registradas para este brief.'

export function briefOptionsLine(brief: Pick<EditorialBrief, 'platform' | 'goal' | 'format'>) {
  return [
    BRIEF_PLATFORM_LABEL[brief.platform],
    BRIEF_GOAL_LABEL[brief.goal],
    BRIEF_FORMAT_LABEL[brief.format],
  ].join(' · ')
}

export function briefFootnote(brief: EditorialBrief): string {
  const pieces = countLabel(brief.evidence.length, 'pieza', 'piezas')
  return `Redactado por ${brief.model} a partir de ${pieces}. Evaluación editorial, no una medición.`
}

export interface BriefPointView {
  text: string
  chips: CitationChip[]
}

export function briefPoints(brief: EditorialBrief): BriefPointView[] {
  return brief.key_points.map((point) => ({
    text: point.text,
    chips: citationChipsFor(point.evidence_urls, brief.evidence),
  }))
}

export function featuredRatioLabel(piece: Evidence): string | null {
  return piece.outlier_ratio == null ? null : formatRatio(piece.outlier_ratio)
}

// Texto plano para pegar en un documento o un chat: lo copiado lleva las fuentes.
export function briefPlainText(brief: EditorialBrief): string {
  const section = (title: string, lines: string[]) => [title, ...lines].join('\n')
  const points = brief.key_points.map((point) =>
    [`- ${point.text}`, ...point.evidence_urls.map((url) => `  ${url}`)].join('\n'),
  )
  const limitations =
    brief.limitations.length > 0 ? brief.limitations.map((item) => `- ${item}`) : [NO_LIMITATIONS]
  return [
    `${brief.topic}\n${briefOptionsLine(brief)}`,
    section('Ángulo', [brief.angle]),
    section('Gancho', [brief.hook ?? HOOK_MISSING]),
    section(
      'Estructura',
      brief.structure.map((step, index) => `${index + 1}. ${step}`),
    ),
    section('Puntos clave', points),
    section('Por qué encaja con 30X', [brief.why_it_fits ?? WHY_IT_FITS_MISSING]),
    section('Qué no sabemos', limitations),
    briefFootnote(brief),
  ].join('\n\n')
}
