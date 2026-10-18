import type { LocationQuery } from 'vue-router'

import type { components } from '@/types/api'

import { BRIEF_FORMAT_LABEL, BRIEF_PLATFORM_LABEL } from './briefView'
import { formatUtcDay, formatUtcTimestamp } from './format'

type Schemas = components['schemas']
type SavedBriefSummary = Schemas['SavedBriefSummary']
type SavedBriefVersion = Schemas['SavedBriefVersion']
type EditorialBrief = Schemas['EditorialBrief']

// `?brief=<id>` abre un brief guardado: el enlace se puede compartir o recargar.
export const SAVED_BRIEF_PARAM = 'brief'
// `?parent=<id>`: el estudio viene de «Cambiar enfoque» en un brief guardado, y lo que genere será
// una versión nueva de ese brief.
export const PARENT_BRIEF_PARAM = 'parent'

const POSITIVE_INTEGER = /^[1-9]\d*$/

function parseId(query: LocationQuery, key: string): number | null {
  const raw = query[key]
  const value = Array.isArray(raw) ? raw[0] : raw
  if (typeof value !== 'string' || !POSITIVE_INTEGER.test(value)) return null
  return Number(value)
}

export function parseSavedBriefId(query: LocationQuery): number | null {
  return parseId(query, SAVED_BRIEF_PARAM)
}

export function parseParentBriefId(query: LocationQuery): number | null {
  return parseId(query, PARENT_BRIEF_PARAM)
}

// «Carrusel · LinkedIn · 17/10»: el tema va aparte, como título de la fila.
export function savedBriefCaption(summary: SavedBriefSummary): string {
  return [
    BRIEF_FORMAT_LABEL[summary.format],
    BRIEF_PLATFORM_LABEL[summary.platform],
    formatUtcDay(summary.created_at),
  ].join(' · ')
}

// Con una sola versión no hay nada que contar.
export function versionCountLabel(count: number): string | null {
  return count > 1 ? `${count} versiones` : null
}

// «v2 · LinkedIn · Post · 18/10, 13:20 UTC»
export function versionLabel(version: SavedBriefVersion): string {
  return [
    `v${version.version}`,
    BRIEF_PLATFORM_LABEL[version.platform],
    BRIEF_FORMAT_LABEL[version.format],
    formatUtcTimestamp(version.created_at),
  ].join(' · ')
}

// Sin id, la API no lo guardó (no hay sesión): no se dice nada.
export function savedBriefNote(brief: EditorialBrief): string | null {
  if (brief.id == null) return null
  if (brief.version != null && brief.version > 1) return `Guardado como versión ${brief.version}`
  return 'Guardado en Mis briefs'
}

// El DELETE borra la cadena entera, no solo la versión que se ve en la fila.
export function deleteConfirmation(summary: SavedBriefSummary): string {
  return summary.version_count > 1
    ? `Se borrarán las ${summary.version_count} versiones de este brief.`
    : 'Se borrará este brief.'
}
