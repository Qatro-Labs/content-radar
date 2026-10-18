import { describe, expect, it } from 'vitest'

import type { components } from '@/types/api'

import {
  briefPlainText,
  briefSentence,
  briefSummary,
  featuredPieces,
  featuredPiecesCaption,
  HOOK_MISSING,
  parseBriefQuery,
  sameRequest,
  serializeBriefQuery,
} from '../briefView'

type Schemas = components['schemas']
type Evidence = Schemas['Evidence']
type EditorialBrief = Schemas['EditorialBrief']

const NO_METRICS = { views: null, likes: null, comments: null, points: null, shares: null }

function piece(url: string, overrides: Partial<Evidence> = {}): Evidence {
  return {
    url,
    source: 'The AI Daily Brief: Artificial Intelligence News',
    platform: 'youtube',
    segment: 'tech',
    title: `Pieza ${url}`,
    published_at: '2026-10-15T10:00:00Z',
    observed_at: '2026-10-17T19:00:00Z',
    metrics: { ...NO_METRICS, views: 1000 },
    outlier_ratio: null,
    is_outlier: null,
    collection: 'automatic',
    replica_count: 0,
    ...overrides,
  }
}

const HN = 'https://news.ycombinator.com/item?id=1'
const YT = 'https://youtube.com/watch?v=1'

function brief(overrides: Partial<EditorialBrief> = {}): EditorialBrief {
  return {
    opportunity_id: 'opp_1552',
    topic: 'Evaluación de agentes de IA',
    platform: 'linkedin',
    goal: 'educate',
    format: 'carousel',
    recommendation: 'publish_now',
    angle: 'Medir un agente es medir un proceso.',
    hook: '¿Cómo sabes que tu piloto funciona?',
    structure: ['El problema', 'Tres cifras'],
    key_points: [{ text: 'Los equipos miden latencia, no resultados.', evidence_urls: [HN, YT] }],
    why_it_fits: 'Habla de decisiones de negocio.',
    evidence: [piece(HN, { platform: 'hackernews', source: 'HN · agents' }), piece(YT)],
    limitations: ['Solo hay dos fuentes.'],
    model: 'claude-haiku-5-5',
    ...overrides,
  }
}

describe('parseBriefQuery', () => {
  it('fills the defaults and marks the link incomplete when options are missing', () => {
    expect(parseBriefQuery({ opportunity: 'opp_1' })).toEqual({
      opportunityId: 'opp_1',
      options: { platform: 'linkedin', goal: 'educate', format: 'post' },
      isComplete: false,
    })
  })

  it('reads a full link as complete', () => {
    const query = {
      opportunity: 'opp_1',
      platform: 'youtube',
      goal: 'generate_leads',
      format: 'short_video',
    }

    expect(parseBriefQuery(query)).toEqual({
      opportunityId: 'opp_1',
      options: { platform: 'youtube', goal: 'generate_leads', format: 'short_video' },
      isComplete: true,
    })
  })

  it('ignores unknown options instead of sending them to the API', () => {
    const parsed = parseBriefQuery({
      opportunity: 'opp_1',
      platform: 'x',
      goal: 'educate',
      format: 'post',
    })

    expect(parsed.options.platform).toBe('linkedin')
    expect(parsed.isComplete).toBe(false)
  })

  it('has no topic without the parameter or with it empty', () => {
    expect(parseBriefQuery({}).opportunityId).toBeNull()
    expect(parseBriefQuery({ opportunity: '' }).opportunityId).toBeNull()
  })

  it('round-trips with serializeBriefQuery', () => {
    const request = {
      opportunity_id: 'opp_1',
      platform: 'newsletter',
      goal: 'spark_conversation',
      format: 'article',
    } as const

    const parsed = parseBriefQuery(serializeBriefQuery(request))

    expect(parsed.isComplete).toBe(true)
    expect(sameRequest({ opportunity_id: 'opp_1', ...parsed.options }, request)).toBe(true)
  })
})

describe('sameRequest', () => {
  const request = {
    opportunity_id: 'opp_1',
    platform: 'linkedin',
    goal: 'educate',
    format: 'post',
  } as const

  it('is false before any brief was asked for and after an option changes', () => {
    expect(sameRequest(undefined, request)).toBe(false)
    expect(sameRequest({ ...request, format: 'carousel' }, request)).toBe(false)
  })
})

describe('featuredPieces', () => {
  it('keeps the three best ratios and leaves pieces without ratio last', () => {
    const pieces = [
      piece('a', { outlier_ratio: 1.2 }),
      piece('b'),
      piece('c', { outlier_ratio: 6.1, is_outlier: true }),
      piece('d', { outlier_ratio: 2.4 }),
    ]

    expect(featuredPieces(pieces).map((item) => item.url)).toEqual(['c', 'd', 'a'])
  })
})

describe('featuredPiecesCaption', () => {
  it('names the total behind the featured pieces', () => {
    expect(featuredPiecesCaption(7)).toBe('las piezas que más pesan de las 7 del tema')
  })

  it('does not talk about weight when every piece is shown', () => {
    expect(featuredPiecesCaption(1)).toBe('la única pieza del tema')
    expect(featuredPiecesCaption(3)).toBe('las 3 piezas del tema')
  })

  it('does not pass the API cap off as the total', () => {
    expect(featuredPiecesCaption(25)).toBe('las que más pesan de las 25 primeras piezas del tema')
  })
})

describe('briefSentence', () => {
  it('reads the options as the sentence of the studio', () => {
    expect(briefSentence({ format: 'post', platform: 'linkedin', goal: 'educate' })).toBe(
      'Post en LinkedIn para educar',
    )
    expect(
      briefSentence({ format: 'short_video', platform: 'newsletter', goal: 'generate_leads' }),
    ).toBe('Vídeo corto en la newsletter para generar leads')
  })
})

describe('briefSummary', () => {
  it('adds how many pieces the brief cites', () => {
    expect(briefSummary(brief())).toBe('Carrusel en LinkedIn para educar · cita 2 piezas')
  })
})

describe('briefPlainText', () => {
  it('carries every section, in screen order, and the source URLs of each key point', () => {
    expect(briefPlainText(brief())).toBe(
      [
        'Evaluación de agentes de IA\nCarrusel en LinkedIn para educar',
        'Gancho\n¿Cómo sabes que tu piloto funciona?',
        'Ángulo\nMedir un agente es medir un proceso.',
        'Estructura\n1. El problema\n2. Tres cifras',
        `Puntos clave\n- Los equipos miden latencia, no resultados.\n  ${HN}\n  ${YT}`,
        'Por qué encaja con 30X\nHabla de decisiones de negocio.',
        'Redactado por claude-haiku-5-5 a partir de 2 piezas. Evaluación editorial, no una medición.',
      ].join('\n\n'),
    )
  })

  it('says the hook is missing instead of leaving a gap', () => {
    expect(briefPlainText(brief({ hook: null }))).toContain(`Gancho\n${HOOK_MISSING}`)
  })
})
