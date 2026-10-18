import { cleanup, fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import fixture from '@fixtures/opportunities.json'
import { resetViewPatch, type RadarQuery } from '@/lib/radarQuery'
import { buildRadarView } from '@/lib/radarView'
import type { components } from '@/types/api'

import RadarHero from '../RadarHero.vue'

const update = vi.fn()

vi.mock('@/composables/useRadarQuery', () => ({ useRadarQuery: () => ({ update }) }))
vi.mock('@/composables/useRadarAgent', () => ({
  useRadarAgent: () => ({ agentRadarParams: ref(null) }),
}))
// El tooltip necesita su provider; aquí solo importa el control que envuelve.
vi.mock('@/components/layout/HoverHint.vue', () => ({
  default: {
    setup: (_: unknown, { slots }: { slots: { default?: () => unknown } }) => slots.default,
  },
}))

// TS lee los enums del JSON como `string`; el fixture cumple el contrato `OpportunityList`.
const list = fixture.opportunities as components['schemas']['OpportunityList']

function query(patch: Partial<RadarQuery> = {}): RadarQuery {
  return {
    lifecycle: [],
    confidence: null,
    topic: null,
    selected: null,
    highlight: [],
    gap: false,
    sort: 'opportunity',
    recommendation: null,
    tab: 'radar',
    ...patch,
  }
}

function renderHero(patch: Partial<RadarQuery> = {}) {
  const radarQuery = query(patch)
  return render(RadarHero, { props: { view: buildRadarView(list, radarQuery), query: radarQuery } })
}

const tile = (label: string) => screen.getByRole('radio', { name: new RegExp(label) })

afterEach(() => {
  cleanup()
  update.mockClear()
})

describe('RadarHero counters', () => {
  it('groups the counters as a single-choice «Filtrar por» group', () => {
    renderHero()
    expect(screen.getByRole('radiogroup', { name: 'Filtrar por' })).toBeTruthy()
    expect(screen.getAllByRole('radio')).toHaveLength(4)
  })

  it('checks «Todos» with the total of topics when the view is untouched', () => {
    renderHero()
    const all = tile('Todos')
    expect(all.getAttribute('aria-checked')).toBe('true')
    expect(all.textContent).toContain(String(list.items.length))
    expect(tile('Acelerando').getAttribute('aria-checked')).toBe('false')
  })

  it('checks the active counter and unchecks «Todos»', () => {
    renderHero({ lifecycle: ['accelerating'] })
    expect(tile('Acelerando').getAttribute('aria-checked')).toBe('true')
    expect(tile('Todos').getAttribute('aria-checked')).toBe('false')
  })

  it('unchecks «Todos» when Rad highlights topics', () => {
    renderHero({ highlight: ['opp_001'] })
    expect(tile('Todos').getAttribute('aria-checked')).toBe('false')
  })

  it('resets the view when «Todos» is pressed', async () => {
    renderHero({ lifecycle: ['emerging'], highlight: ['opp_002'] })
    await fireEvent.click(tile('Todos'))
    expect(update).toHaveBeenCalledWith(resetViewPatch())
  })

  it('keeps the «reset» anchor for Rad on «Todos»', () => {
    renderHero()
    expect(tile('Todos').getAttribute('data-agent')).toBe('reset')
    expect(screen.queryByRole('button', { name: 'Restablecer vista' })).toBeNull()
  })
})
