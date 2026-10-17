import { describe, expect, it } from 'vitest'

import fixture from '@fixtures/opportunities.json'
import type { components } from '@/types/api'

import {
  buildExploreView,
  exploreSummary,
  parseExploreFilter,
  parseExploreText,
  type ExploreFilter,
} from '../exploreView'

type Schemas = components['schemas']
type Evidence = Schemas['Evidence']
type TopicEvidence = Schemas['TopicEvidence']
type Opportunity = Schemas['Opportunity']
type OpportunityList = Schemas['OpportunityList']

// TS lee los enums del JSON como `string`; el fixture cumple el contrato `OpportunityList`.
const base = (fixture.opportunities as OpportunityList).items[0]!

const NO_METRICS = { views: null, likes: null, comments: null, points: null, shares: null }

function topic(id: string, outlierCount: number): Opportunity {
  return { ...base, id, topic: `Tema ${id}`, outlier_count: outlierCount }
}

function piece(url: string, overrides: Partial<Evidence> = {}): Evidence {
  return {
    url,
    source: 'Canal',
    platform: 'youtube',
    segment: 'tech',
    title: `Pieza ${url}`,
    published_at: '2026-10-10T10:00:00Z',
    observed_at: '2026-10-17T19:00:00Z',
    metrics: { ...NO_METRICS, views: 1000 },
    outlier_ratio: null,
    is_outlier: null,
    collection: 'automatic',
    replica_count: 0,
    ...overrides,
  }
}

function inTopic(opportunityId: string, pieces: Evidence[]): TopicEvidence[] {
  return pieces.map((item) => ({ ...item, opportunity_id: opportunityId }))
}

function topicPieces(opportunityId: string, count: number): TopicEvidence[] {
  const pieces = Array.from({ length: count }, (_, index) =>
    piece(`https://example.com/${opportunityId}/${index}`),
  )
  return inTopic(opportunityId, pieces)
}

const shared = piece('https://news.ycombinator.com/item?id=3', {
  platform: 'hackernews',
  source: 'HN · Claude',
  outlier_ratio: 1.0,
  is_outlier: false,
  published_at: '2026-10-11T08:00:00Z',
})

const evidenceByTopic = {
  // La pieza compartida llega antes desde opp_b: tiene que quedarse con opp_a, de mejor puesto.
  opp_b: [
    shared,
    piece('https://xataka.com/a', {
      platform: 'rss',
      source: 'Xataka · Inteligencia artificial',
      title: 'Nuevos modelos abiertos',
      metrics: NO_METRICS,
      published_at: '2026-10-15T09:00:00Z',
    }),
    piece('https://youtube.com/watch?v=2', {
      source: 'Matthew Berman',
      outlier_ratio: 5.0,
      is_outlier: true,
      published_at: '2026-10-14T12:00:00Z',
    }),
  ],
  opp_a: [
    piece('https://youtube.com/watch?v=1', {
      title: 'Inteligencia artificial en la empresa',
      outlier_ratio: 2.4,
      is_outlier: false,
    }),
    piece('https://news.ycombinator.com/item?id=1', {
      platform: 'hackernews',
      source: 'HN · OpenAI',
      title: 'Las matemáticas de la IA',
      metrics: { ...NO_METRICS, points: 420 },
      outlier_ratio: 5.0,
      is_outlier: true,
      published_at: '2026-10-12T10:00:00Z',
    }),
    shared,
  ],
  opp_c: [
    piece('https://elpais.com/b', {
      platform: 'rss',
      source: 'El País',
      metrics: NO_METRICS,
      published_at: '2026-10-16T07:00:00Z',
    }),
  ],
}

// GET /evidence, flat as the API serves it.
const evidence = Object.entries(evidenceByTopic).flatMap(([id, pieces]) => inTopic(id, pieces))

// API order: opp_a is rank 1. opp_d has no pieces in the evidence.
const opportunities = [topic('opp_a', 1), topic('opp_b', 3), topic('opp_c', 0), topic('opp_d', 3)]

function view(filter: ExploreFilter | null = null, text = '') {
  return buildExploreView({ opportunities, evidence, filter, text })
}

const urls = (pieces: { url: string }[]) => pieces.map((item) => item.url)

describe('buildExploreView', () => {
  it('sorts by ratio, breaks ties by recency and leaves pieces without ratio at the end', () => {
    expect(urls(view().pieces)).toEqual([
      'https://youtube.com/watch?v=2',
      'https://news.ycombinator.com/item?id=1',
      'https://youtube.com/watch?v=1',
      'https://news.ycombinator.com/item?id=3',
      'https://elpais.com/b',
      'https://xataka.com/a',
    ])
  })

  it('keeps a piece shared by two topics once, under the topic with the better rank', () => {
    const shown = view().pieces.filter((item) => item.url === shared.url)

    expect(shown).toHaveLength(1)
    expect(shown[0]?.opportunity.id).toBe('opp_a')
    expect(shown[0]?.rank).toBe(1)
  })

  it('counts every piece regardless of the active filter', () => {
    const expected = { total: 6, outliers: 2, youtube: 2, hackernews: 2, rss: 2 }

    expect(view().counts).toEqual(expected)
    expect(view('youtube').counts).toEqual(expected)
  })

  it.each([
    ['outliers', ['https://youtube.com/watch?v=2', 'https://news.ycombinator.com/item?id=1']],
    ['youtube', ['https://youtube.com/watch?v=2', 'https://youtube.com/watch?v=1']],
    [
      'hackernews',
      ['https://news.ycombinator.com/item?id=1', 'https://news.ycombinator.com/item?id=3'],
    ],
  ] as const)('keeps only the %s pieces in sorted order', (filter, expected) => {
    expect(urls(view(filter).visible)).toEqual(expected)
  })

  it.each([
    ['ignores case', 'inteligencia', ['https://youtube.com/watch?v=1', 'https://xataka.com/a']],
    ['ignores accents', 'MATEMATICAS', ['https://news.ycombinator.com/item?id=1']],
    ['matches the source', 'el país', ['https://elpais.com/b']],
  ])('filters by text and %s', (_, text, expected) => {
    expect(urls(view(null, text).visible)).toEqual(expected)
  })

  it('reports the published range and the topics with pieces', () => {
    const result = view()

    expect(result.publishedRange).toEqual({ from: '10/10', to: '16/10' })
    expect(result.topicsWithPiecesCount).toBe(3)
    expect(result.isCapped).toBe(false)
  })

  it('groups interleaved pieces by opportunity_id and skips topics outside the list', () => {
    const interleaved = [
      ...inTopic('opp_b', [piece('https://a.com/1')]),
      ...inTopic('opp_a', [piece('https://a.com/2')]),
      ...inTopic('opp_gone', [piece('https://a.com/3')]),
      ...inTopic('opp_b', [piece('https://a.com/4')]),
    ]
    const result = buildExploreView({
      opportunities: [topic('opp_a', 0), topic('opp_b', 0)],
      evidence: interleaved,
      filter: null,
      text: '',
    })

    expect(result.pieces.map((item) => [item.url, item.opportunity.id, item.rank])).toEqual([
      ['https://a.com/2', 'opp_a', 1],
      ['https://a.com/1', 'opp_b', 2],
      ['https://a.com/4', 'opp_b', 2],
    ])
    expect(result.topicsWithPiecesCount).toBe(2)
  })

  it('ranks topics by outliers, breaks ties by rank and leaves out topics without outliers', () => {
    expect(view().topTopics.map((item) => item.id)).toEqual(['opp_b', 'opp_d', 'opp_a'])
  })

  it('ranks sources by outlier pieces and breaks ties alphabetically', () => {
    const outlier = { outlier_ratio: 3.2, is_outlier: true }
    const result = buildExploreView({
      opportunities: [topic('opp_a', 4)],
      evidence: inTopic('opp_a', [
        piece('https://youtube.com/watch?v=10', { ...outlier, source: 'Wes Roth' }),
        piece('https://youtube.com/watch?v=11', { ...outlier, source: 'Matthew Berman' }),
        piece('https://youtube.com/watch?v=12', { ...outlier, source: 'midudev' }),
        piece('https://youtube.com/watch?v=13', { ...outlier, source: 'Matthew Berman' }),
        piece('https://youtube.com/watch?v=14', { source: 'OpenAI', outlier_ratio: 2.1 }),
      ]),
      filter: null,
      text: '',
    })

    expect(result.topSources).toEqual([
      { source: 'Matthew Berman', count: 2, share: 1 },
      { source: 'midudev', count: 1, share: 0.5 },
      { source: 'Wes Roth', count: 1, share: 0.5 },
    ])
  })

  it('flags the list as capped when a topic reaches the 25 pieces the API serves at most', () => {
    const result = buildExploreView({
      opportunities: [topic('opp_a', 0)],
      evidence: topicPieces('opp_a', 25),
      filter: null,
      text: '',
    })

    expect(result.isCapped).toBe(true)
  })

  it('counts the cap per topic, not across topics', () => {
    const result = buildExploreView({
      opportunities: [topic('opp_a', 0), topic('opp_b', 0)],
      evidence: [...topicPieces('opp_a', 24), ...topicPieces('opp_b', 1)],
      filter: null,
      text: '',
    })

    expect(result.isCapped).toBe(false)
  })

  it('has no published range, no top sources and no topics without pieces', () => {
    const result = buildExploreView({
      opportunities: [topic('opp_a', 0)],
      evidence: [],
      filter: null,
      text: '',
    })

    expect(result.topicsWithPiecesCount).toBe(0)
    expect(result.publishedRange).toBeNull()
    expect(result.topSources).toEqual([])
    expect(result.topTopics).toEqual([])
  })
})

describe('parseExploreFilter', () => {
  it.each([
    ['a valid filter', { filter: 'youtube' }, 'youtube'],
    ['an unknown filter', { filter: 'rss' }, null],
    ['no filter', {}, null],
    ['a repeated param', { filter: ['outliers', 'youtube'] }, 'outliers'],
  ])('reads %s', (_, query, expected) => {
    expect(parseExploreFilter(query)).toBe(expected)
  })
})

describe('parseExploreText', () => {
  it.each([
    ['the text as written', { q: 'Xataka · IA ' }, 'Xataka · IA '],
    ['no text', {}, ''],
    ['a repeated param', { q: ['Xataka', 'HN'] }, 'Xataka'],
  ])('reads %s', (_, query, expected) => {
    expect(parseExploreText(query)).toBe(expected)
  })
})

describe('exploreSummary', () => {
  it('describes the served pieces with the real figures', () => {
    const summary = exploreSummary({
      counts: { total: 356, outliers: 27, youtube: 96, hackernews: 145, rss: 115 },
      topicsWithPiecesCount: 38,
      publishedRange: { from: '04/10', to: '17/10' },
      isCapped: true,
    })

    expect(summary).toBe(
      '356 piezas de los 38 temas, publicadas entre el 04/10 y el 17/10. ' +
        '27 rinden 3× o más que su canal. Hasta 25 piezas por tema.',
    )
  })

  it('uses the singular for one piece, one topic and one day', () => {
    const summary = exploreSummary({
      counts: { total: 1, outliers: 1, youtube: 1, hackernews: 0, rss: 0 },
      topicsWithPiecesCount: 1,
      publishedRange: { from: '07/10', to: '07/10' },
      isCapped: false,
    })

    expect(summary).toBe('1 pieza de 1 tema, publicada el 07/10. 1 rinde 3× o más que su canal.')
  })

  it('groups thousands', () => {
    const summary = exploreSummary({
      counts: { total: 1363, outliers: 0, youtube: 0, hackernews: 1363, rss: 0 },
      topicsWithPiecesCount: 60,
      publishedRange: { from: '01/10', to: '17/10' },
      isCapped: false,
    })

    expect(summary).toMatch(/^1\.363 piezas de los 60 temas/)
  })
})
