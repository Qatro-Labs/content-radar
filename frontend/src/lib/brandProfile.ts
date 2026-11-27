import type { components } from '@/types/api'

import { BRIEF_FORMAT_WORD, BRIEF_PLATFORM_LABEL, BRIEF_PLATFORM_WORD } from './briefView'

type Schemas = components['schemas']
type RadarProfile = Schemas['RadarProfile']
type PublishingDay = Schemas['PublishingDay']
type Weekday = Schemas['Weekday']
type EditorialBrief = Schemas['EditorialBrief']

export type BrandDraft = RadarProfile
export type BrandDraftErrors = Partial<Record<keyof BrandDraft, string>>

// Los mismos límites que `backend/app/schemas/profile.py`: si cambian allí, cambian aquí.
export const MAX_TONE_WORDS = 3
const MAX_TONE_WORD_CHARS = 30
const MAX_SHORT_TEXT = 200
const MAX_LONG_TEXT = 600
const MAX_LANGUAGES = 3
const MAX_PUBLISHING_DAYS = 7
const LANGUAGE_CODE = /^[a-z]{2}$/

export const EXAMPLE_TOPIC = 'Tema de ejemplo'

export const WEEKDAYS = [
  'mon',
  'tue',
  'wed',
  'thu',
  'fri',
  'sat',
  'sun',
] as const satisfies readonly Weekday[]
export const WEEKDAY_LABEL: Record<Weekday, string> = {
  mon: 'Lunes',
  tue: 'Martes',
  wed: 'Miércoles',
  thu: 'Jueves',
  fri: 'Viernes',
  sat: 'Sábado',
  sun: 'Domingo',
}

// Sugerencias para elegir con un clic; las palabras guardadas que no están aquí se añaden a la
// lista (`toneOptions`) para que nunca desaparezcan del formulario.
const TONE_SUGGESTIONS = ['directo', 'práctico', 'cercano', 'experto', 'con humor']

// Un día nuevo copia el canal y el formato del primero: lo normal es publicar casi siempre en el
// mismo sitio.
const FIRST_DAY_FALLBACK: Omit<PublishingDay, 'day'> = { channel: 'linkedin', format: 'post' }

const REQUIRED_MESSAGE = 'Este campo no puede quedar vacío.'

export interface BrandPreviewModel {
  isExample: boolean
  topic: string
  hook: string | null
  audience: string
  region: string
  callToAction: string | null
  tone: string[]
  neverSay: string | null
  weeklyLine: string
}

export function toDraft(profile: RadarProfile): BrandDraft {
  return {
    ...profile,
    languages: [...profile.languages],
    tone: [...profile.tone],
    publishing_days: profile.publishing_days.map((entry) => ({ ...entry })),
  }
}

function tooLong(limit: number): string {
  return `Máximo ${limit} caracteres.`
}

function requiredTextError(value: string, limit: number): string | undefined {
  const trimmed = value.trim()
  if (trimmed === '') return REQUIRED_MESSAGE
  return trimmed.length > limit ? tooLong(limit) : undefined
}

function optionalTextError(value: string, limit: number): string | undefined {
  return value.trim().length > limit ? tooLong(limit) : undefined
}

function toneError(tone: string[]): string | undefined {
  const words = tone.map((word) => word.trim())
  if (words.length === 0 || words.length > MAX_TONE_WORDS) return 'Elige entre 1 y 3 palabras.'
  if (words.some((word) => word === '')) return 'Ninguna palabra puede quedar vacía.'
  if (words.some((word) => word.length > MAX_TONE_WORD_CHARS)) {
    return `Cada palabra, máximo ${MAX_TONE_WORD_CHARS} caracteres.`
  }
  return undefined
}

function languagesError(languages: string[]): string | undefined {
  if (languages.length === 0 || languages.length > MAX_LANGUAGES)
    return 'Elige entre 1 y 3 idiomas.'
  return languages.every((code) => LANGUAGE_CODE.test(code)) ? undefined : 'Idioma no válido.'
}

function publishingDaysError(days: PublishingDay[]): string | undefined {
  if (days.length === 0 || days.length > MAX_PUBLISHING_DAYS) return 'Elige entre 1 y 7 días.'
  const unique = new Set(days.map((entry) => entry.day))
  return unique.size === days.length ? undefined : 'Cada día solo puede aparecer una vez.'
}

export function draftErrors(draft: BrandDraft): BrandDraftErrors {
  const errors: BrandDraftErrors = {
    creates_about: requiredTextError(draft.creates_about, MAX_SHORT_TEXT),
    audience: requiredTextError(draft.audience, MAX_LONG_TEXT),
    target_region: requiredTextError(draft.target_region, MAX_SHORT_TEXT),
    call_to_action: optionalTextError(draft.call_to_action, MAX_SHORT_TEXT),
    out_of_scope: optionalTextError(draft.out_of_scope, MAX_LONG_TEXT),
    never_say: optionalTextError(draft.never_say, MAX_LONG_TEXT),
    tone: toneError(draft.tone),
    languages: languagesError(draft.languages),
    publishing_days: publishingDaysError(draft.publishing_days),
  }
  return Object.fromEntries(
    Object.entries(errors).filter(([, message]) => message !== undefined),
  ) as BrandDraftErrors
}

function byWeekday(days: PublishingDay[]): PublishingDay[] {
  return [...days].sort((a, b) => WEEKDAYS.indexOf(a.day) - WEEKDAYS.indexOf(b.day))
}

// El backend recorta los espacios y no le importa el orden de los días: lo que guardaría igual no
// cuenta como cambio.
function normalized(profile: RadarProfile): RadarProfile {
  return {
    creates_about: profile.creates_about.trim(),
    audience: profile.audience.trim(),
    goal: profile.goal,
    target_region: profile.target_region.trim(),
    languages: profile.languages,
    out_of_scope: profile.out_of_scope.trim(),
    tone: profile.tone.map((word) => word.trim()),
    call_to_action: profile.call_to_action.trim(),
    never_say: profile.never_say.trim(),
    publishing_days: byWeekday(profile.publishing_days),
  }
}

export function isDirty(draft: BrandDraft, profile: RadarProfile): boolean {
  return JSON.stringify(normalized(draft)) !== JSON.stringify(normalized(profile))
}

export function toSavedProfile(draft: BrandDraft): RadarProfile {
  return normalized(draft)
}

function joinWithAnd(words: string[]): string {
  if (words.length <= 1) return words.join('')
  return `${words.slice(0, -1).join(', ')} y ${words.at(-1)}`
}

function weeklyLine(days: PublishingDay[]): string {
  const count = days.length
  const pieces = `${count} ${count === 1 ? 'pieza' : 'piezas'} por semana`
  const channels = [...new Set(days.map((entry) => entry.channel))]
  if (channels.length === 0) return `${pieces}.`
  return `${pieces}, con formatos para ${joinWithAnd(channels.map((c) => BRIEF_PLATFORM_WORD[c]))}.`
}

function textOrNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

export function previewOf(draft: BrandDraft, brief: EditorialBrief | null): BrandPreviewModel {
  return {
    isExample: brief === null,
    topic: brief?.topic ?? EXAMPLE_TOPIC,
    hook: brief?.hook ?? null,
    audience: draft.audience.trim(),
    region: draft.target_region.trim(),
    callToAction: textOrNull(draft.call_to_action),
    tone: draft.tone,
    neverSay: textOrNull(draft.never_say),
    weeklyLine: weeklyLine(draft.publishing_days),
  }
}

export function publishingSummary(days: PublishingDay[]): string {
  return byWeekday(days)
    .map(
      (entry) =>
        `${WEEKDAY_LABEL[entry.day]} · ${BRIEF_FORMAT_WORD[entry.format]} en ${BRIEF_PLATFORM_LABEL[entry.channel]}`,
    )
    .join(' — ')
}

export function toneOptions(selected: string[]): string[] {
  return [...new Set([...TONE_SUGGESTIONS, ...selected])]
}

export function toggleTone(tone: string[], word: string): string[] {
  if (tone.includes(word)) return tone.filter((current) => current !== word)
  return tone.length >= MAX_TONE_WORDS ? tone : [...tone, word]
}

export function toggleDay(days: PublishingDay[], day: Weekday): PublishingDay[] {
  if (days.some((entry) => entry.day === day)) return days.filter((entry) => entry.day !== day)
  const template = days[0] ?? FIRST_DAY_FALLBACK
  return byWeekday([...days, { day, channel: template.channel, format: template.format }])
}

export function capitalized(word: string): string {
  return word.charAt(0).toLocaleUpperCase('es') + word.slice(1)
}
