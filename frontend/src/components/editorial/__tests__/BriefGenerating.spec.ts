import { cleanup, render, screen, within } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import { CHECK_EXPECTED_AT_MS, FINISH_HOLD_MS, READ_PER_PIECE_MS } from '@/lib/briefStages'
import { DEFAULT_BRIEF_OPTIONS } from '@/lib/briefView'
import type { components } from '@/types/api'

import BriefGenerating from '../BriefGenerating.vue'

type Evidence = components['schemas']['Evidence']

function piece(source: string, title: string): Evidence {
  return {
    url: `https://example.com/${encodeURIComponent(title)}`,
    source,
    platform: 'youtube',
    segment: 'tech',
    title,
    published_at: '2026-10-15T10:00:00Z',
    observed_at: '2026-10-17T19:00:00Z',
    metrics: { views: 12_000, likes: null, comments: null, points: null, shares: null },
    outlier_ratio: 8.6,
    is_outlier: true,
    collection: 'automatic',
    replica_count: 0,
  }
}

const PIECES = [
  piece('AI Engineer', 'Tokenomics 101'),
  piece('McKinsey Insights: Artificial Intelligence', 'What does AI really cost?'),
  piece('OpenAI', 'Stop Overpaying for Intelligence'),
]

function renderWaiting(props: { pieces?: Evidence[]; done?: boolean } = {}) {
  return render(BriefGenerating, {
    props: {
      pieces: PIECES,
      pieceCount: 7,
      options: DEFAULT_BRIEF_OPTIONS,
      done: false,
      ...props,
    },
  })
}

async function advance(ms: number) {
  await vi.advanceTimersByTimeAsync(ms)
  await nextTick()
}

function stageTitle() {
  return screen.getByRole('status').textContent?.trim()
}

// jsdom no implementa matchMedia: sin él, VueUse entiende que no hay preferencia de movimiento.
function preferReducedMotion() {
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches: query.includes('prefers-reduced-motion: reduce'),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }))
}

describe('BriefGenerating', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  // Sin `globals` de Vitest, Testing Library no desmonta solo entre tests.
  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('starts reading the real pieces of the topic', () => {
    renderWaiting()

    expect(screen.getByRole('region', { name: 'Generando el brief' }).ariaBusy).toBe('true')
    expect(stageTitle()).toBe('Leyendo las piezas del tema')
    expect(screen.getByText('Post en LinkedIn para educar · unos 15 s')).toBeTruthy()
    expect(screen.getByText('What does AI really cost?')).toBeTruthy()
    expect(screen.getByText('y 4 piezas más del tema')).toBeTruthy()
  })

  it('narrates the pipeline in order: read, draft, then check the citations', async () => {
    const { container } = renderWaiting()

    await advance(PIECES.length * READ_PER_PIECE_MS)
    expect(stageTitle()).toBe('Redactando el gancho y el ángulo')
    const draft = container.querySelector<HTMLElement>('[data-generating-draft]')!
    expect(within(draft).getByText('Gancho')).toBeTruthy()
    expect(within(draft).queryByRole('listitem', { hidden: true })).toBeNull()

    await advance(CHECK_EXPECTED_AT_MS - PIECES.length * READ_PER_PIECE_MS)
    expect(stageTitle()).toBe('Comprobando cada cita contra su fuente')
    const chips = within(draft).getAllByRole('listitem', { hidden: true })
    expect(chips.map((chip) => chip.textContent?.trim())).toEqual([
      'AI Engineer',
      'McKinsey Insights',
      'OpenAI',
    ])
  })

  it('holds on the last stage until the API answers', async () => {
    const { emitted } = renderWaiting()

    await advance(60_000)

    expect(stageTitle()).toBe('Comprobando cada cita contra su fuente')
    expect(emitted().finished).toBeUndefined()
  })

  it('closes once the brief arrives and says it is finished exactly once', async () => {
    const { emitted, rerender } = renderWaiting()
    await advance(CHECK_EXPECTED_AT_MS)

    await rerender({ done: true })
    await advance(0)
    expect(stageTitle()).toBe('Brief listo')
    expect(emitted().finished).toBeUndefined()

    await advance(FINISH_HOLD_MS)
    expect(emitted().finished).toHaveLength(1)

    await advance(10 * FINISH_HOLD_MS)
    expect(emitted().finished).toHaveLength(1)
  })

  it('fast-forwards when the brief arrives while Rad is still reading', async () => {
    const { emitted, rerender } = renderWaiting()
    await advance(READ_PER_PIECE_MS / 2)

    await rerender({ done: true })
    await advance(0)

    expect(stageTitle()).toBe('Brief listo')
    expect(screen.getAllByRole('img', { name: 'Leída' })).toHaveLength(PIECES.length)
    await advance(2 * FINISH_HOLD_MS)
    expect(emitted().finished).toHaveLength(1)
  })

  it('skips the reading when there are no pieces', () => {
    renderWaiting({ pieces: [] })

    expect(stageTitle()).toBe('Redactando el gancho y el ángulo')
  })

  it('shows the brief as soon as it arrives with reduced motion', async () => {
    preferReducedMotion()
    const { emitted, rerender } = renderWaiting()
    await nextTick()

    await rerender({ done: true })
    await nextTick()

    expect(emitted().finished).toHaveLength(1)
  })
})
