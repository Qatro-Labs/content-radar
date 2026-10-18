import { describe, expect, it } from 'vitest'

import type { components } from '@/types/api'

import {
  CHECK_EXPECTED_AT_MS,
  citationSources,
  CITATION_STEP_MS,
  CLOSING_CITATION_STEP_MS,
  DRAFT_REVEAL_MS,
  FINISH_BLINK_DELAY_MS,
  FINISH_HOLD_MS,
  type GenerationInput,
  generationTimelineAt,
  pieceStatus,
  READ_PER_PIECE_MS,
} from '../briefStages'

type Evidence = components['schemas']['Evidence']

// Lo habitual: tres piezas destacadas de tres fuentes distintas, y la API todavía sin responder.
const WAITING: GenerationInput = {
  elapsedMs: 0,
  pieceCount: 3,
  citationCount: 3,
  doneAtMs: null,
}

function at(elapsedMs: number, overrides: Partial<GenerationInput> = {}) {
  return generationTimelineAt({ ...WAITING, elapsedMs, ...overrides })
}

function piece(source: string): Evidence {
  return {
    url: `https://example.com/${source}`,
    source,
    platform: 'youtube',
    segment: 'tech',
    title: 'Pieza',
    published_at: '2026-10-15T10:00:00Z',
    observed_at: '2026-10-17T19:00:00Z',
    metrics: { views: 1000, likes: null, comments: null, points: null, shares: null },
    outlier_ratio: null,
    is_outlier: null,
    collection: 'automatic',
    replica_count: 0,
  }
}

describe('generationTimelineAt', () => {
  it('reads the featured pieces one after another', () => {
    expect(at(0)).toMatchObject({ stage: 'read', readingIndex: 0, readCount: 0 })
    expect(at(READ_PER_PIECE_MS)).toMatchObject({ stage: 'read', readingIndex: 1, readCount: 1 })
    expect(at(3 * READ_PER_PIECE_MS - 1)).toMatchObject({ readingIndex: 2, readCount: 2 })
  })

  it('drafts once every piece is read, until the check is due', () => {
    expect(at(3 * READ_PER_PIECE_MS)).toMatchObject({
      stage: 'draft',
      readingIndex: null,
      readCount: 3,
    })
    expect(at(CHECK_EXPECTED_AT_MS - 1).stage).toBe('draft')
  })

  it('goes straight to the draft when there are no pieces to read', () => {
    expect(at(0, { pieceCount: 0, citationCount: 0 })).toMatchObject({
      stage: 'draft',
      readingIndex: null,
      readCount: 0,
    })
  })

  it('checks one citation at a time but leaves the last one for the response', () => {
    expect(at(CHECK_EXPECTED_AT_MS)).toMatchObject({ stage: 'check', checkedCount: 0 })
    expect(at(CHECK_EXPECTED_AT_MS + CITATION_STEP_MS).checkedCount).toBe(1)
    // Sin respuesta, se queda en 2 de 3 por mucho que tarde.
    expect(at(60_000)).toMatchObject({ stage: 'check', checkedCount: 2, isFinished: false })
  })

  it('never finishes while the API has not answered', () => {
    expect(at(120_000).isFinished).toBe(false)
  })

  it('closes after the hold when the response arrives late', () => {
    const doneAtMs = 30_000

    expect(at(doneAtMs, { doneAtMs })).toMatchObject({
      stage: 'done',
      hasBlinked: false,
      isFinished: false,
    })
    expect(at(doneAtMs + FINISH_BLINK_DELAY_MS, { doneAtMs }).hasBlinked).toBe(true)
    expect(at(doneAtMs + FINISH_HOLD_MS - 1, { doneAtMs }).isFinished).toBe(false)
    expect(at(doneAtMs + FINISH_HOLD_MS, { doneAtMs }).isFinished).toBe(true)
    expect(at(doneAtMs + 10 * FINISH_HOLD_MS, { doneAtMs }).isFinished).toBe(true)
  })

  it('completes the last citation once the response arrives', () => {
    const doneAtMs = 30_000

    expect(at(doneAtMs, { doneAtMs }).checkedCount).toBe(3)
  })

  it('fast-forwards a response that arrives mid-read and lets the draft show before closing', () => {
    const doneAtMs = 500

    expect(at(doneAtMs, { doneAtMs })).toMatchObject({
      stage: 'done',
      readingIndex: null,
      readCount: 3,
      checkedCount: 1,
    })
    // Las citas que faltan se completan deprisa, una tras otra.
    expect(at(doneAtMs + 2 * CLOSING_CITATION_STEP_MS, { doneAtMs }).checkedCount).toBe(3)
    // El borrador apareció al responder: el cierre espera a que termine de dibujarse.
    expect(at(doneAtMs + FINISH_HOLD_MS, { doneAtMs }).isFinished).toBe(false)
    expect(at(doneAtMs + DRAFT_REVEAL_MS, { doneAtMs }).isFinished).toBe(true)
  })

  it('closes a source-less wait without citations', () => {
    const doneAtMs = 5000

    expect(at(doneAtMs, { pieceCount: 0, citationCount: 0, doneAtMs })).toMatchObject({
      stage: 'done',
      readCount: 0,
      checkedCount: 0,
    })
  })
})

describe('pieceStatus', () => {
  it('marks pieces as read, being read or still pending', () => {
    const reading = at(READ_PER_PIECE_MS)

    expect([0, 1, 2].map((index) => pieceStatus(reading, index))).toEqual([
      'read',
      'reading',
      'pending',
    ])
  })
})

describe('citationSources', () => {
  it('cites each source once, by its short name', () => {
    const pieces = [
      piece('The AI Daily Brief: Artificial Intelligence News'),
      piece('Xataka · Inteligencia artificial'),
      piece('The AI Daily Brief: Artificial Intelligence News'),
    ]

    expect(citationSources(pieces)).toEqual(['The AI Daily Brief', 'Xataka'])
  })
})
