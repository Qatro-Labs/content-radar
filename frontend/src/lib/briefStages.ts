import type { components } from '@/types/api'

import { shortSourceName } from './evidenceFormat'

type Evidence = components['schemas']['Evidence']

// Concepto C1 «Rad lee y subraya» (canvas de Crear, 18/10). POST /editorial/brief no da progreso:
// devuelve el brief entero de una vez, en unos 15 s (≈1 s si está cacheado). Mientras tanto, la
// espera cuenta el pipeline real del backend en su orden —leer la evidencia del tema, redactar con
// el LLM y comprobar cada cita en Python— con tiempos estimados, y la última etapa espera a la
// respuesta. Sin porcentajes ni contadores: nada sugiere un avance que no se mide (CLAUDE.md §2.3).

export const GenerationStage = {
  Read: 'read',
  Draft: 'draft',
  Check: 'check',
  // La API ya respondió: el cierre antes de enseñar el brief.
  Done: 'done',
} as const
export type GenerationStage = (typeof GenerationStage)[keyof typeof GenerationStage]

const STAGE_ORDER: readonly GenerationStage[] = [
  GenerationStage.Read,
  GenerationStage.Draft,
  GenerationStage.Check,
  GenerationStage.Done,
]

export const GENERATION_TITLE: Record<GenerationStage, string> = {
  read: 'Leyendo las piezas del tema',
  draft: 'Redactando el gancho y el ángulo',
  check: 'Comprobando cada cita contra su fuente',
  done: 'Brief listo',
}

// La misma estimación que da BriefSkeleton («Tarda unos 15 s»).
export const TYPICAL_WAIT_LABEL = 'unos 15 s'

export const GENERATION_STEPS = [
  { stage: GenerationStage.Read, label: 'Leer la evidencia' },
  { stage: GenerationStage.Draft, label: 'Redactar' },
  { stage: GenerationStage.Check, label: 'Comprobar citas' },
] as const

// Lo que tarda Rad en leer cada pieza destacada: el subrayado, el check y la fuente que vuela
// hasta él.
export const READ_PER_PIECE_MS = 1100
// Redactar es casi toda la espera. La comprobación de citas es instantánea en Python, así que se
// cuenta hacia el final de los ~15 s y desde ahí la vista espera a la respuesta.
export const CHECK_EXPECTED_AT_MS = 11_000
// Si la lectura se alargara, el borrador sigue a la vista al menos esto antes de comprobar.
export const DRAFT_MIN_MS = 3000
export const CITATION_STEP_MS = 500
// Al responder la API, las citas que faltan se completan deprisa.
export const CLOSING_CITATION_STEP_MS = 120
// RadMark tarda 380 ms en volver de radar a ojo: parpadea cuando ya es un ojo.
export const FINISH_BLINK_DELAY_MS = 380
// El cierre («Brief listo», las citas en lima, el parpadeo) antes de enseñar el resultado.
export const FINISH_HOLD_MS = 700

// La forma del borrador: secciones reales del brief y huesos de tinta en lugar de texto, que no
// existe hasta que responde la API. Anchos en % de la línea.
export const DRAFT_SKETCH = [
  { label: 'Gancho', bones: [92, 64], isTall: true },
  { label: 'Ángulo', bones: [100, 96, 58], isTall: false },
  { label: 'Puntos clave', bones: [88], isTall: false },
] as const
export const BONE_LEAD_MS = 100
export const BONE_STAGGER_MS = 130
export const BONE_DRAW_MS = 520
const BONE_COUNT = DRAFT_SKETCH.reduce((total, section) => total + section.bones.length, 0)
// Si la API responde antes de que se vea el borrador, el cierre espera a que termine de dibujarse.
export const DRAFT_REVEAL_MS = BONE_LEAD_MS + (BONE_COUNT - 1) * BONE_STAGGER_MS + BONE_DRAW_MS

export interface GenerationInput {
  // Tiempo desde que apareció la espera.
  elapsedMs: number
  // Piezas que lee Rad (las destacadas) y fuentes distintas que cita.
  pieceCount: number
  citationCount: number
  // Cuándo respondió la API, en el mismo reloj; `null` mientras espera.
  doneAtMs: number | null
}

export interface GenerationTimeline {
  stage: GenerationStage
  // La pieza que Rad lee ahora; `null` fuera de la lectura.
  readingIndex: number | null
  // Las primeras `readCount` piezas ya están leídas, y las primeras `checkedCount` citas,
  // comprobadas.
  readCount: number
  checkedCount: number
  hasBlinked: boolean
  isFinished: boolean
}

function readEndMs(pieceCount: number): number {
  return pieceCount * READ_PER_PIECE_MS
}

function checkStartMs(pieceCount: number): number {
  return Math.max(readEndMs(pieceCount) + DRAFT_MIN_MS, CHECK_EXPECTED_AT_MS)
}

function waitingTimeline({
  elapsedMs,
  pieceCount,
  citationCount,
}: GenerationInput): GenerationTimeline {
  const waiting = {
    readingIndex: null,
    readCount: pieceCount,
    checkedCount: 0,
    hasBlinked: false,
    isFinished: false,
  }
  if (elapsedMs < readEndMs(pieceCount)) {
    const readingIndex = Math.floor(elapsedMs / READ_PER_PIECE_MS)
    return { ...waiting, stage: GenerationStage.Read, readingIndex, readCount: readingIndex }
  }
  const sinceCheckMs = elapsedMs - checkStartMs(pieceCount)
  if (sinceCheckMs < 0) return { ...waiting, stage: GenerationStage.Draft }
  // La última cita espera a la respuesta: la comprobación de verdad llega con ella.
  const checkedCount = Math.min(
    Math.floor(sinceCheckMs / CITATION_STEP_MS),
    Math.max(citationCount - 1, 0),
  )
  return { ...waiting, stage: GenerationStage.Check, checkedCount }
}

function closingTimeline(input: GenerationInput, doneAtMs: number): GenerationTimeline {
  const { elapsedMs, pieceCount, citationCount } = input
  const sinceDoneMs = elapsedMs - doneAtMs
  const checkedAtDone = waitingTimeline({ ...input, elapsedMs: doneAtMs }).checkedCount
  const caughtUp = Math.floor(sinceDoneMs / CLOSING_CITATION_STEP_MS) + 1
  // Con una respuesta temprana, todas las piezas cuentan como leídas y el borrador sale al cerrar.
  const draftShownAtMs = Math.min(readEndMs(pieceCount), doneAtMs)
  const finishAtMs = Math.max(doneAtMs + FINISH_HOLD_MS, draftShownAtMs + DRAFT_REVEAL_MS)
  return {
    stage: GenerationStage.Done,
    readingIndex: null,
    readCount: pieceCount,
    checkedCount: Math.min(citationCount, checkedAtDone + caughtUp),
    hasBlinked: sinceDoneMs >= FINISH_BLINK_DELAY_MS,
    isFinished: elapsedMs >= finishAtMs,
  }
}

export function generationTimelineAt(input: GenerationInput): GenerationTimeline {
  const { elapsedMs, doneAtMs } = input
  if (doneAtMs !== null && elapsedMs >= doneAtMs) return closingTimeline(input, doneAtMs)
  return waitingTimeline(input)
}

export function isSameTimeline(a: GenerationTimeline, b: GenerationTimeline): boolean {
  return (Object.keys(a) as (keyof GenerationTimeline)[]).every((key) => a[key] === b[key])
}

export type TrackerStatus = 'done' | 'current' | 'pending'

export function trackerStatus(step: GenerationStage, current: GenerationStage): TrackerStatus {
  const distance = STAGE_ORDER.indexOf(step) - STAGE_ORDER.indexOf(current)
  if (distance < 0) return 'done'
  return distance === 0 ? 'current' : 'pending'
}

export type PieceStatus = 'pending' | 'reading' | 'read'

export function pieceStatus(timeline: GenerationTimeline, index: number): PieceStatus {
  if (index < timeline.readCount) return 'read'
  return index === timeline.readingIndex ? 'reading' : 'pending'
}

// Las fuentes de las piezas que lee Rad, sin repetir: las citas que comprueba al final.
export function citationSources(pieces: readonly Evidence[]): string[] {
  return [...new Set(pieces.map((piece) => shortSourceName(piece.source)))]
}
