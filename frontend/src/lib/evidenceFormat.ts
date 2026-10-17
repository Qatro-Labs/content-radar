import type { components } from '@/types/api'

import { formatDecimal } from './opportunityFormat'

type Schemas = components['schemas']
type Evidence = Schemas['Evidence']
type Metrics = Schemas['Metrics']
type Platform = Schemas['Platform']
type Rate = Schemas['Rate']
type Segment = Schemas['Segment']

export const PLATFORM_LABEL: Record<Platform, string> = {
  youtube: 'YouTube',
  hackernews: 'Hacker News',
  rss: 'RSS',
  brave: 'Brave',
  linkedin: 'LinkedIn',
  instagram: 'Instagram',
  tiktok: 'TikTok',
}

// DESIGN.md §9: `latam_es` mezcla España y Latinoamérica, así que se rotula "En español".
export const SEGMENT_LABEL: Record<Segment, string> = {
  tech: 'Tech',
  business: 'Negocio',
  latam_es: 'En español',
}

// es-ES no agrupa los números de 4 cifras por defecto ("1363"); DESIGN.md §9 quiere "1.363".
// `useGrouping: 'always'` es ECMA-402 (2023) y lo aceptan los navegadores, pero la lib de
// TypeScript todavía lo tipa como boolean: de ahí el cast.
const ALWAYS_GROUP = { useGrouping: 'always' } as unknown as Intl.NumberFormatOptions
const groupedCount = new Intl.NumberFormat('es-ES', {
  ...ALWAYS_GROUP,
  maximumFractionDigits: 0,
})

export function formatCount(count: number): string {
  return groupedCount.format(count)
}

// "1 fuente", "0 fuentes", "1.363 fuentes".
export function countLabel(count: number, singular: string, plural: string): string {
  return `${formatCount(count)} ${count === 1 ? singular : plural}`
}

const METRIC_LABELS: readonly [keyof Metrics, string][] = [
  ['views', 'vistas'],
  ['points', 'puntos'],
  ['likes', 'me gusta'],
  ['comments', 'comentarios'],
  ['shares', 'compartidos'],
]
const METRIC_SEPARATOR = ' · '

// Las métricas tal como las da la fuente; `null` si no expone ninguna (RSS).
export function formatMetrics(metrics: Metrics): string | null {
  const parts = METRIC_LABELS.flatMap(([key, label]) => {
    const value = metrics[key]
    return value == null ? [] : [`${formatCount(value)} ${label}`]
  })
  return parts.length === 0 ? null : parts.join(METRIC_SEPARATOR)
}

const VELOCITY_UNIT_LABEL: Record<string, string> = {
  'views/h': 'vistas/h',
  'points/h': 'puntos/h',
}
// Por debajo de 10 un decimal todavía dice algo ("2,4 puntos/h"); por encima es ruido.
const VELOCITY_DECIMALS_BELOW = 10

export function formatVelocity(velocity: Rate | null | undefined): string | null {
  if (velocity == null) return null
  const { value, unit } = velocity
  const shown =
    value === 0 || value >= VELOCITY_DECIMALS_BELOW ? formatCount(value) : formatDecimal(value)
  return `${shown} ${VELOCITY_UNIT_LABEL[unit] ?? unit}`
}

export function formatRatio(ratio: number): string {
  return `${formatDecimal(ratio)}×`
}

// CLAUDE.md §7: ≥ 3× es outlier (lo decide la API con `is_outlier`) y ≥ 2× es destacada.
export const HIGHLIGHT_RATIO_MIN = 2

export type RatioLabel = 'Outlier' | 'Destacada'

export function ratioLabel(evidence: Evidence): RatioLabel | null {
  if (evidence.is_outlier === true) return 'Outlier'
  if (evidence.outlier_ratio != null && evidence.outlier_ratio >= HIGHLIGHT_RATIO_MIN) {
    return 'Destacada'
  }
  return null
}

function hasAnyMetric(metrics: Metrics): boolean {
  return Object.values(metrics).some((value) => value != null)
}

// Sin ratio hay dos causas distintas: RSS no publica métricas, y algunas piezas de YouTube sí
// las tienen pero su canal no tiene historial suficiente como referencia (docs/brief.md §7).
export function missingRatioLabel(evidence: Evidence): string {
  if (evidence.platform === 'rss' || !hasAnyMetric(evidence.metrics)) {
    return 'Sin métricas públicas'
  }
  return 'Sin línea base del canal'
}

// DESIGN.md §4: la barra "Rendimiento frente a su canal" llega hasta 6× con marcas en 1× y 3×.
export const PERFORMANCE_SCALE_MAX = 6
export const PERFORMANCE_MARKS = [1, 3] as const

export function performanceFraction(ratio: number): number {
  return Math.min(Math.max(ratio, 0) / PERFORMANCE_SCALE_MAX, 1)
}

// HN no tiene canal: su referencia es el p90 de la búsqueda (CLAUDE.md §7).
export const PERFORMANCE_LEGEND =
  '1× = mediana del canal (YouTube, ajustada por la edad de la pieza) o p90 de la búsqueda ' +
  '(Hacker News). 3× = outlier. La barra llega hasta 6×.'
export const VELOCITY_NOTE = 'Velocidad entre la primera y la última medición.'

// "Xataka · Inteligencia artificial" → "Xataka"; "The AI Daily Brief: Artificial…" → "The AI
// Daily Brief". El nombre corto basta para un chip; el completo sigue en la fila de la pieza.
const SOURCE_NAME_SEPARATORS = /\s·\s|:/

export function shortSourceName(source: string): string {
  return source.split(SOURCE_NAME_SEPARATORS)[0]?.trim() || source
}
