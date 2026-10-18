import { cleanup, render, screen } from '@testing-library/vue'
import { afterEach, describe, expect, it } from 'vitest'

import { HOOK_MISSING } from '@/lib/briefView'
import type { components } from '@/types/api'

import BriefResult from '../BriefResult.vue'

type Schemas = components['schemas']

const HN = 'https://news.ycombinator.com/item?id=1'
const OUTSIDE = 'https://example.com/not-in-evidence'

const BRIEF: Schemas['EditorialBrief'] = {
  opportunity_id: 'opp_1552',
  topic: 'Evaluación de agentes de IA',
  platform: 'linkedin',
  goal: 'educate',
  format: 'carousel',
  recommendation: 'publish_now',
  angle: 'Medir un agente es medir un proceso.',
  hook: null,
  structure: ['El problema'],
  key_points: [{ text: 'Los equipos miden latencia.', evidence_urls: [HN, OUTSIDE] }],
  why_it_fits: null,
  evidence: [
    {
      url: HN,
      source: 'HN · agents',
      platform: 'hackernews',
      segment: 'tech',
      title: 'Evaluating agents',
      published_at: '2026-10-15T10:00:00Z',
      observed_at: '2026-10-17T19:00:00Z',
      metrics: { views: null, likes: null, comments: 12, points: 80, shares: null },
      outlier_ratio: 4.2,
      is_outlier: true,
      collection: 'automatic',
      replica_count: 0,
    },
  ],
  limitations: [],
  model: 'claude-haiku-5-5',
}

describe('BriefResult', () => {
  // Sin `globals` de Vitest, Testing Library no desmonta solo entre tests.
  afterEach(cleanup)

  it('says what is missing instead of leaving gaps', () => {
    render(BriefResult, { props: { brief: BRIEF } })

    expect(screen.getByText(HOOK_MISSING)).toBeTruthy()
    expect(screen.getByText(/Encaje no disponible/)).toBeTruthy()
    expect(screen.getByText('No hay limitaciones registradas para este brief.')).toBeTruthy()
  })

  it('links each key point to its sources in a new tab', () => {
    render(BriefResult, { props: { brief: BRIEF } })

    const sourceLink = screen.getByRole('link', { name: 'HN' })
    expect(sourceLink.getAttribute('href')).toBe(HN)
    expect(sourceLink.getAttribute('target')).toBe('_blank')
    // Una cita fuera de la evidencia servida se nombra por su host.
    expect(screen.getByRole('link', { name: 'example.com' }).getAttribute('href')).toBe(OUTSIDE)
  })

  it('labels the text as an editorial evaluation with its model', () => {
    render(BriefResult, { props: { brief: BRIEF } })

    expect(
      screen.getByText(
        'Redactado por claude-haiku-5-5 a partir de 1 pieza. Evaluación editorial, no una medición.',
      ),
    ).toBeTruthy()
  })
})
