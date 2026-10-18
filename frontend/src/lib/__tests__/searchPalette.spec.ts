import { describe, expect, it } from 'vitest'

import fixture from '@fixtures/opportunities.json'
import type { components } from '@/types/api'

import { buildSearchResults, hasResults, MAX_RESULTS_PER_GROUP } from '../searchPalette'

type Schemas = components['schemas']
type TopicEvidence = Schemas['TopicEvidence']
type Opportunity = Schemas['Opportunity']
type OpportunityList = Schemas['OpportunityList']

// TS lee los enums del JSON como `string`; el fixture cumple el contrato `OpportunityList`.
const base = (fixture.opportunities as OpportunityList).items[0]!

function topic(id: string, name: string): Opportunity {
  return { ...base, id, topic: name }
}

function piece(opportunityId: string, url: string, title: string, source: string): TopicEvidence {
  return {
    opportunity_id: opportunityId,
    url,
    source,
    platform: 'rss',
    segment: 'latam_es',
    title,
    published_at: '2026-10-15T09:00:00Z',
    observed_at: '2026-10-17T19:00:00Z',
    metrics: { views: null, likes: null, comments: null, points: null, shares: null },
    outlier_ratio: null,
    is_outlier: null,
    collection: 'automatic',
    replica_count: 0,
  }
}

const opportunities = [
  topic('opp_a', 'Agentes de IA en la empresa'),
  topic('opp_b', 'Modelos abiertos'),
]

const evidence = [
  piece('opp_a', 'https://xataka.com/1', 'Cómo usar AGENTES en ventas', 'Xataka'),
  piece('opp_a', 'https://xataka.com/2', 'La IA llega a la banca', 'Xataka'),
  // Repetida en otro tema: cuenta una vez y se atribuye a opp_a, de mejor puesto.
  piece('opp_b', 'https://xataka.com/1', 'Cómo usar AGENTES en ventas', 'Xataka'),
  piece('opp_b', 'https://hn.com/1', 'Open weights everywhere', 'HN · Llama'),
]

describe('buildSearchResults', () => {
  it('ignores case and accents in both the text and the data', () => {
    const results = buildSearchResults({ opportunities, evidence, text: '  AGÉNTES ' })

    expect(results.topics.map((t) => t.id)).toEqual(['opp_a'])
    expect(results.pieces.map((p) => [p.url, p.opportunity.id])).toEqual([
      ['https://xataka.com/1', 'opp_a'],
    ])
    expect(results.sources).toEqual([])
  })

  it('matches pieces by their source too', () => {
    const results = buildSearchResults({ opportunities, evidence, text: 'llama' })

    expect(results.pieces.map((p) => p.title)).toEqual(['Open weights everywhere'])
    expect(results.sources).toEqual([{ source: 'HN · Llama', pieceCount: 1 }])
  })

  it('lists each source once with its distinct pieces, most pieces first', () => {
    const results = buildSearchResults({ opportunities, evidence, text: '' })

    expect(results.sources).toEqual([
      { source: 'Xataka', pieceCount: 2 },
      { source: 'HN · Llama', pieceCount: 1 },
    ])
  })

  it(`shows at most ${MAX_RESULTS_PER_GROUP} results per group, in ranking order`, () => {
    const many = Array.from({ length: MAX_RESULTS_PER_GROUP + 3 }, (_, index) =>
      topic(`opp_${index}`, `Agentes ${index}`),
    )
    const manyPieces = many.map((_, index) =>
      piece('opp_0', `https://medio${index}.com`, `Agentes ${index}`, `Agentes al día ${index}`),
    )

    const results = buildSearchResults({
      opportunities: many,
      evidence: manyPieces,
      text: 'agentes',
    })

    expect(results.topics.map((t) => t.id)).toEqual(
      many.slice(0, MAX_RESULTS_PER_GROUP).map((t) => t.id),
    )
    expect(results.pieces).toHaveLength(MAX_RESULTS_PER_GROUP)
    expect(results.sources).toHaveLength(MAX_RESULTS_PER_GROUP)
  })

  it('returns three empty groups when nothing matches', () => {
    const results = buildSearchResults({ opportunities, evidence, text: 'blockchain' })

    expect(results).toEqual({ topics: [], pieces: [], sources: [] })
    expect(hasResults(results)).toBe(false)
  })

  it('finds topics before any evidence has loaded', () => {
    const results = buildSearchResults({ opportunities, evidence: [], text: 'modelos' })

    expect(results.topics.map((t) => t.id)).toEqual(['opp_b'])
    expect(hasResults(results)).toBe(true)
  })
})
