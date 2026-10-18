import type { components } from '@/types/api'

import type { Lifecycle } from './radarQuery'

type Schemas = components['schemas']
type Opportunity = Schemas['Opportunity']
type Recommendation = Schemas['Recommendation']
type GrowthStatus = Schemas['GrowthStatus']
type Confidence = Schemas['Confidence']
type TimelinePoint = Schemas['TimelinePoint']

// Los scores del contrato van de 0 a 100 (CLAUDE.md §6).
export const SCORE_MAX = 100
export const PERCENT = 100
// DESIGN.md §9: un dato ausente se escribe así, nunca 0 ni guion (CLAUDE.md §2, regla 3).
export const NOT_AVAILABLE = 'no disponible'
// DESIGN.md §9: el signo menos tipográfico (U+2212), no el guion.
const MINUS_SIGN = '−'

// DESIGN.md §9: espacio antes de %, no separable para que "+100 %" no parta el "%" a otra línea.
const PERCENT_SUFFIX = '\u00a0%'

function roundedPercent(acceleration: number): number {
  return Math.round(acceleration * PERCENT)
}

export function formatAcceleration(acceleration: number): string {
  if (!Number.isFinite(acceleration)) return NOT_AVAILABLE
  const percent = roundedPercent(acceleration)
  if (percent > 0) return `↑ +${percent}${PERCENT_SUFFIX}`
  if (percent < 0) return `↓ ${MINUS_SIGN}${Math.abs(percent)}${PERCENT_SUFFIX}`
  return `→ 0${PERCENT_SUFFIX}`
}

// Sobre la cifra que se muestra: −0,004 se lee "→ 0 %" y no debe pintarse como descenso.
export function isDeclining(acceleration: number): boolean {
  return Number.isFinite(acceleration) && roundedPercent(acceleration) < 0
}

export function formatShare(share: number): string {
  return `${Math.round(share * PERCENT)}${PERCENT_SUFFIX}`
}

// DESIGN.md §9: decimales con coma ("6,1×").
const oneDecimal = new Intl.NumberFormat('es-ES', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

export function formatDecimal(value: number): string {
  return oneDecimal.format(value)
}

export function formatScore(score: number | null | undefined): string {
  if (score == null) return NOT_AVAILABLE
  return String(Math.round(score))
}

// DESIGN.md §9: umbrales iniciales de la banda de encaje, ajustables con Melkin.
const FIT_BAND_HIGH_MIN = 67
const FIT_BAND_MEDIUM_MIN = 34

export type FitBand = 'Alto' | 'Medio' | 'Bajo'

export function fitBand(fit: number): FitBand {
  if (fit >= FIT_BAND_HIGH_MIN) return 'Alto'
  if (fit >= FIT_BAND_MEDIUM_MIN) return 'Medio'
  return 'Bajo'
}

export function formatFit(fit: number | null | undefined): string {
  if (fit == null) return NOT_AVAILABLE
  // La banda se calcula sobre la cifra que se muestra: 66,6 se lee "67" y tiene que decir "Alto".
  const shown = Math.round(fit)
  return `${fitBand(shown)} · ${shown}`
}

interface PulseTier {
  reached: (acceleration: number) => boolean
  seconds: number
}

// Tabla de DESIGN.md §7: solo late lo que crece, y más rápido cuanto más acelera. Los dos
// primeros umbrales son inclusivos y los dos últimos, estrictos, como en la tabla.
const PULSE_TIERS: readonly PulseTier[] = [
  { reached: (acceleration) => acceleration >= 1.0, seconds: 1.4 },
  { reached: (acceleration) => acceleration >= 0.5, seconds: 2.0 },
  { reached: (acceleration) => acceleration > 0.2, seconds: 2.8 },
  { reached: (acceleration) => acceleration > 0, seconds: 3.6 },
]

export function pulsePeriodSeconds(lifecycle: Lifecycle, acceleration: number): number | null {
  if (lifecycle === 'unknown') return null
  return PULSE_TIERS.find((tier) => tier.reached(acceleration))?.seconds ?? null
}

// DESIGN.md §8: `18 + 0.34·s` px, con `s` = `evidence_strength` (0–100).
// Radar compacto, al lado del ranking: burbujas un tercio más pequeñas que en DESIGN.md §8.
const BUBBLE_MIN_PX = 12
const BUBBLE_PX_PER_STRENGTH = 0.24

export function bubbleSize(evidenceStrength: number): number {
  return Math.round(BUBBLE_MIN_PX + BUBBLE_PX_PER_STRENGTH * evidenceStrength)
}

// Lecturas de "Para quién importa" de CLAUDE.md §7. FIT_HIGH_MIN no es la banda "Alto" (67): es
// el umbral de encaje que pide `publish_now`.
const TECH_HEAVY_MIN = 0.6
const BUSINESS_LOW_MAX = 0.3
const FIT_HIGH_MIN = 60

type AudienceSignals = Pick<Opportunity, 'audience_mix' | 'audience_fit_score' | 'latam_gap'>

function needsBusinessTranslation({ audience_mix, audience_fit_score }: AudienceSignals): boolean {
  return (
    audience_mix.tech >= TECH_HEAVY_MIN &&
    audience_mix.business < BUSINESS_LOW_MAX &&
    audience_fit_score != null &&
    audience_fit_score >= FIT_HIGH_MIN
  )
}

// Se usa `latam_gap` y no `audience_mix.latam_es`, que mezcla España y Latinoamérica
// (CLAUDE.md §7): el front no recalcula el hueco.
export function audienceReading(signals: AudienceSignals): string {
  if (needsBusinessTranslation(signals)) {
    return 'Mucho tech y poco negocio: todavía no llegó a ejecutivos. Hay que traducirlo a negocio.'
  }
  if (signals.latam_gap === true) {
    return 'Ya se habla de su uso en empresas y casi no hay evidencia de fuentes latinoamericanas.'
  }
  if (signals.latam_gap === false) {
    return 'Ya hay cobertura en fuentes latinoamericanas: conviene buscar otro ángulo.'
  }
  return 'Con estos datos no hay una lectura clara de audiencia.'
}

export function latamGapLabel(latamGap: boolean | null): string {
  if (latamGap === true) return 'hueco en LATAM'
  if (latamGap === false) return 'ya cubierto en LATAM'
  return `hueco en LATAM ${NOT_AVAILABLE}`
}

// Etiquetas fijas de DESIGN.md §9.
export const RECOMMENDATION_LABEL: Record<Recommendation, string> = {
  publish_now: 'Publicar ya',
  find_angle: 'Buscar ángulo',
  wait_for_case: 'Esperar caso',
  discard: 'Descartar',
}

// Cómo repiten el chip los motivos de backend/app/intelligence/ranking.py («Publicar: …»,
// «Esperar: …»); junto al chip, sobra. «Publicar ya con ángulo propio: …» conserva el matiz
// («Con ángulo propio: …») y «Tema saturado: …» se queda: es la causa, no la etiqueta.
const RESTATED_LABEL: Record<Recommendation, RegExp | null> = {
  publish_now: /^Publicar(?: ya)?:?\s*/,
  find_angle: /^Buscar ángulo:\s*/,
  wait_for_case: /^Esperar(?: caso)?:\s*/,
  discard: null,
}

export function recommendationReasonText(opportunity: Opportunity): string | null {
  const reason = opportunity.recommendation_reason
  if (!reason) return null
  const restated = RESTATED_LABEL[opportunity.recommendation]
  const rest = restated ? reason.replace(restated, '') : reason
  return rest.charAt(0).toUpperCase() + rest.slice(1)
}

export const GROWTH_LABEL: Record<GrowthStatus, string> = {
  observed: 'Observado',
  estimated: 'Estimado',
  preliminary: 'Preliminar',
}

// En las listas, «Observado» es lo normal y no se repite en cada fila: solo se marca lo que no lo
// es. El detalle (vista previa, expediente) sigue diciendo los tres (CLAUDE.md §2.5).
export function growthCaveat(status: GrowthStatus): string | null {
  return status === 'observed' ? null : GROWTH_LABEL[status]
}

export interface WindowTotals {
  current: number
  previous: number
}

// Piezas nuevas de cada ventana del timeline. Acompañan a la aceleración, no la sustituyen: la
// aceleración va ajustada por volumen (CLAUDE.md §7) y no es la resta de estas cifras.
export function windowTotals(points: readonly TimelinePoint[]): WindowTotals | null {
  if (points.length === 0) return null
  const sum = (window: TimelinePoint['window']) =>
    points
      .filter((point) => point.window === window)
      .reduce((total, point) => total + point.count, 0)
  return { current: sum('current'), previous: sum('previous') }
}

// Se escribe detrás de "confianza": "confianza alta".
export const CONFIDENCE_LABEL: Record<Confidence, string> = {
  high: 'alta',
  medium: 'media',
  low: 'baja',
}
