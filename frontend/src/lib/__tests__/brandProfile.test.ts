import { describe, expect, it } from 'vitest'

import type { components } from '@/types/api'

import {
  draftErrors,
  EXAMPLE_TOPIC,
  isDirty,
  previewOf,
  publishingSummary,
  toDraft,
  toggleDay,
  toggleTone,
  toneOptions,
} from '../brandProfile'

type Schemas = components['schemas']
type RadarProfile = Schemas['RadarProfile']
type EditorialBrief = Schemas['EditorialBrief']

const PROFILE: RadarProfile = {
  creates_about: 'Crecimiento de empresas con IA',
  audience: 'Dueños y líderes de empresas',
  goal: 'educate',
  target_region: 'Latinoamérica',
  languages: ['es'],
  out_of_scope: 'Programación a fondo',
  tone: ['directo', 'práctico'],
  call_to_action: '',
  never_say: 'Promesas sin evidencia',
  publishing_days: [
    { day: 'mon', channel: 'instagram', format: 'short_video' },
    { day: 'wed', channel: 'instagram', format: 'carousel' },
    { day: 'fri', channel: 'instagram', format: 'short_video' },
  ],
}

const BRIEF: EditorialBrief = {
  opportunity_id: 'opp_001',
  topic: 'Agentes de IA en ventas',
  platform: 'linkedin',
  goal: 'educate',
  format: 'post',
  recommendation: 'publish_now',
  angle: 'Un ángulo',
  hook: 'Tu equipo de ventas ya compite con un agente.',
  structure: [],
  key_points: [],
  evidence: [],
  limitations: [],
  model: 'claude-haiku-5-5',
}

describe('brandProfile', () => {
  it('toDraft copies the profile so editing the draft never touches the cached one', () => {
    const draft = toDraft(PROFILE)
    draft.tone.push('cercano')
    draft.publishing_days[0]!.channel = 'youtube'

    expect(PROFILE.tone).toEqual(['directo', 'práctico'])
    expect(PROFILE.publishing_days[0]!.channel).toBe('instagram')
    expect(draftErrors(toDraft(PROFILE))).toEqual({})
  })

  it('draftErrors flags a fourth tone word and a repeated day', () => {
    const draft = toDraft(PROFILE)
    draft.tone = ['directo', 'práctico', 'cercano', 'experto']
    draft.publishing_days = [
      { day: 'mon', channel: 'instagram', format: 'post' },
      { day: 'mon', channel: 'linkedin', format: 'post' },
    ]

    const errors = draftErrors(draft)

    expect(errors.tone).toBe('Elige entre 1 y 3 palabras.')
    expect(errors.publishing_days).toBe('Cada día solo puede aparecer una vez.')
  })

  it('draftErrors applies the backend limits to required and long text', () => {
    const draft = toDraft(PROFILE)
    draft.audience = '   '
    draft.target_region = 'x'.repeat(201)
    draft.never_say = 'x'.repeat(601)
    draft.call_to_action = 'x'.repeat(200)
    draft.tone = ['x'.repeat(31)]
    draft.publishing_days = []

    const errors = draftErrors(draft)

    expect(errors.audience).toBe('Este campo no puede quedar vacío.')
    expect(errors.target_region).toBe('Máximo 200 caracteres.')
    expect(errors.never_say).toBe('Máximo 600 caracteres.')
    expect(errors.call_to_action).toBeUndefined()
    expect(errors.tone).toBe('Cada palabra, máximo 30 caracteres.')
    expect(errors.publishing_days).toBe('Elige entre 1 y 7 días.')
  })

  it('isDirty ignores surrounding spaces and the order of the days', () => {
    const draft = toDraft(PROFILE)
    expect(isDirty(draft, PROFILE)).toBe(false)

    draft.never_say = '  Promesas sin evidencia  '
    draft.publishing_days.reverse()
    expect(isDirty(draft, PROFILE)).toBe(false)

    draft.never_say = 'Otra cosa'
    expect(isDirty(draft, PROFILE)).toBe(true)
  })

  it('previewOf uses the latest brief topic and hook, or a marked example without briefs', () => {
    const draft = toDraft(PROFILE)

    const fromBrief = previewOf(draft, BRIEF)
    expect(fromBrief.isExample).toBe(false)
    expect(fromBrief.topic).toBe(BRIEF.topic)
    expect(fromBrief.hook).toBe(BRIEF.hook)

    const example = previewOf(draft, null)
    expect(example.isExample).toBe(true)
    expect(example.topic).toBe(EXAMPLE_TOPIC)
    expect(example.hook).toBeNull()
    expect(example.weeklyLine).toBe('3 piezas por semana, con formatos para Instagram.')
  })

  it('previewOf reflects the draft call to action and never_say immediately', () => {
    const draft = toDraft(PROFILE)
    expect(previewOf(draft, BRIEF).callToAction).toBeNull()

    draft.call_to_action = 'agendar una llamada'
    draft.never_say = 'Hablar de la competencia'
    draft.tone = ['cercano']
    draft.audience = 'Equipos de marketing'
    draft.target_region = 'México'
    draft.publishing_days = [
      { day: 'tue', channel: 'linkedin', format: 'post' },
      { day: 'thu', channel: 'newsletter', format: 'article' },
    ]

    const preview = previewOf(draft, BRIEF)
    expect(preview.callToAction).toBe('agendar una llamada')
    expect(preview.neverSay).toBe('Hablar de la competencia')
    expect(preview.tone).toEqual(['cercano'])
    expect(preview.audience).toBe('Equipos de marketing')
    expect(preview.region).toBe('México')
    expect(preview.weeklyLine).toBe(
      '2 piezas por semana, con formatos para LinkedIn y la newsletter.',
    )

    draft.publishing_days = [{ day: 'mon', channel: 'instagram', format: 'short_video' }]
    expect(previewOf(draft, BRIEF).weeklyLine).toBe(
      '1 pieza por semana, con formatos para Instagram.',
    )
  })

  it('toneOptions keeps the saved words and toggleTone never passes three', () => {
    expect(toneOptions(['irónico'])).toContain('irónico')
    expect(toneOptions(['directo']).filter((word) => word === 'directo')).toHaveLength(1)

    expect(toggleTone(['directo'], 'directo')).toEqual([])
    expect(toggleTone(['a', 'b', 'c'], 'd')).toEqual(['a', 'b', 'c'])
    expect(toggleTone(['a'], 'b')).toEqual(['a', 'b'])
  })

  it('toggleDay adds a day in weekday order with the channel of the first day, or removes it', () => {
    const added = toggleDay(PROFILE.publishing_days, 'tue')
    expect(added.map((entry) => entry.day)).toEqual(['mon', 'tue', 'wed', 'fri'])
    expect(added[1]).toEqual({ day: 'tue', channel: 'instagram', format: 'short_video' })

    expect(toggleDay(PROFILE.publishing_days, 'wed').map((entry) => entry.day)).toEqual([
      'mon',
      'fri',
    ])
  })

  it('publishingSummary reads the days as a sentence', () => {
    expect(publishingSummary(PROFILE.publishing_days)).toBe(
      'Lunes · vídeo corto en Instagram — Miércoles · carrusel en Instagram — Viernes · vídeo corto en Instagram',
    )
  })
})
