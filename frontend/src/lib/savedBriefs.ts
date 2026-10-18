import type { LocationQuery } from 'vue-router'

import type { components } from '@/types/api'

import { BRIEF_FORMAT_LABEL, BRIEF_PLATFORM_LABEL } from './briefView'
import { formatUtcDay } from './format'

type SavedBriefSummary = components['schemas']['SavedBriefSummary']

// `?brief=<id>` abre un brief guardado: el enlace se puede compartir o recargar.
export const SAVED_BRIEF_PARAM = 'brief'

const POSITIVE_INTEGER = /^[1-9]\d*$/

export function parseSavedBriefId(query: LocationQuery): number | null {
  const raw = query[SAVED_BRIEF_PARAM]
  const value = Array.isArray(raw) ? raw[0] : raw
  if (typeof value !== 'string' || !POSITIVE_INTEGER.test(value)) return null
  return Number(value)
}

// «Carrusel · LinkedIn · 17/10»: el tema va aparte, como título de la fila.
export function savedBriefCaption(summary: SavedBriefSummary): string {
  return [
    BRIEF_FORMAT_LABEL[summary.format],
    BRIEF_PLATFORM_LABEL[summary.platform],
    formatUtcDay(summary.created_at),
  ].join(' · ')
}
