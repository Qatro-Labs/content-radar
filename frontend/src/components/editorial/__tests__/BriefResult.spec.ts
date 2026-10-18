import { cleanup, fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { briefPlainText, HOOK_MISSING } from '@/lib/briefView'
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

// jsdom no tiene API de portapapeles ni `execCommand`: useClipboard cae a su copia de respaldo
// (un textarea y `execCommand('copy')`), así que basta con leer el textarea en ese momento.
function captureCopies(): string[] {
  const copies: string[] = []
  document.execCommand = vi.fn(() => {
    copies.push(document.querySelector('textarea')?.value ?? '')
    return true
  })
  return copies
}

describe('BriefResult', () => {
  // Sin `globals` de Vitest, Testing Library no desmonta solo entre tests.
  afterEach(cleanup)

  it('keeps its actions at hand and hands the edit back to the studio', async () => {
    const { emitted } = render(BriefResult, { props: { brief: BRIEF } })

    expect(screen.getByText('Carrusel en LinkedIn para educar · cita 1 pieza')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Copiar enlace' })).toBeTruthy()

    await fireEvent.click(screen.getByRole('button', { name: 'Cambiar enfoque' }))

    expect(emitted('edit')).toHaveLength(1)
  })

  it('copies the brief as plain text and says so', async () => {
    const copies = captureCopies()
    render(BriefResult, { props: { brief: BRIEF } })

    await fireEvent.click(screen.getByRole('button', { name: 'Copiar brief' }))

    expect(copies).toEqual([briefPlainText(BRIEF)])
    expect(await screen.findByRole('button', { name: 'Brief copiado' })).toBeTruthy()
    expect(screen.getByRole('status').textContent).toContain(
      'Brief copiado, con las URLs de cada punto',
    )
  })

  it('copies the link that reopens this brief', async () => {
    const copies = captureCopies()
    render(BriefResult, { props: { brief: BRIEF } })

    await fireEvent.click(screen.getByRole('button', { name: 'Copiar enlace' }))

    expect(copies).toEqual([window.location.href])
    expect(await screen.findByRole('button', { name: 'Enlace copiado' })).toBeTruthy()
    expect(screen.getByRole('status').textContent).toContain(
      'Enlace copiado: abre este mismo brief',
    )
  })

  it('says what is missing instead of leaving gaps', () => {
    render(BriefResult, { props: { brief: BRIEF } })

    expect(screen.getByText(HOOK_MISSING)).toBeTruthy()
    expect(screen.getByText(/Encaje no disponible/)).toBeTruthy()
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
