import { cleanup, fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, describe, expect, it } from 'vitest'

import fixture from '@fixtures/opportunities.json'
import type { components } from '@/types/api'

import BriefComposer from '../BriefComposer.vue'

type Schemas = components['schemas']

// TS lee los enums del JSON como `string`; el fixture cumple el contrato `OpportunityList`.
const base = (fixture.opportunities as Schemas['OpportunityList']).items[0]!
const evidence = (fixture.evidence as Record<string, Schemas['Evidence'][]>)[base.id]!

const OPTIONS = { platform: 'linkedin', goal: 'educate', format: 'post' } as const
const LOADED = { data: evidence, isPending: false, isError: false }

function renderComposer(
  overrides: { opportunity?: Schemas['Opportunity']; pending?: boolean } = {},
) {
  return render(BriefComposer, {
    props: {
      opportunity: overrides.opportunity ?? base,
      evidence: LOADED,
      pending: overrides.pending ?? false,
      options: OPTIONS,
    },
  })
}

describe('BriefComposer', () => {
  // Sin `globals` de Vitest, Testing Library no desmonta solo entre tests.
  afterEach(cleanup)

  it('reads the options as a sentence with one button per slot', () => {
    renderComposer()

    expect(screen.getByRole('button', { name: 'Formato: post' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Plataforma: LinkedIn' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Objetivo: educar' })).toBeTruthy()
  })

  it('opens a slot into its options, one slot at a time', async () => {
    renderComposer()
    const format = screen.getByRole('button', { name: 'Formato: post' })

    await fireEvent.click(format)

    expect(format.getAttribute('aria-expanded')).toBe('true')
    const group = document.getElementById(format.getAttribute('aria-controls')!)
    expect(group?.textContent).toContain('Carrusel')

    await fireEvent.click(screen.getByRole('button', { name: 'Plataforma: LinkedIn' }))

    expect(format.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByRole('button', { name: 'Carrusel' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Instagram' })).toBeTruthy()
  })

  it('writes the picked option back and closes the slot without generating', async () => {
    const { emitted } = renderComposer()
    await fireEvent.click(screen.getByRole('button', { name: 'Formato: post' }))

    await fireEvent.click(screen.getByRole('button', { name: 'Carrusel' }))

    expect(emitted('update:options')).toEqual([[{ ...OPTIONS, format: 'carousel' }]])
    expect(emitted('generate')).toBeUndefined()
    expect(screen.queryByRole('group')).toBeNull()
  })

  it('closes the open slot with Escape', async () => {
    renderComposer()
    const goal = screen.getByRole('button', { name: 'Objetivo: educar' })
    await fireEvent.click(goal)

    await fireEvent.keyDown(screen.getByRole('button', { name: 'Generar leads' }), {
      key: 'Escape',
    })

    expect(goal.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByRole('group')).toBeNull()
  })

  it('shows the pieces it will write from, outliers with their badge', () => {
    renderComposer()

    expect(
      screen.getByText('Con qué lo escribirá · las 3 piezas del tema', { exact: false }),
    ).toBeTruthy()
    expect(screen.getByText('6,1×')).toBeTruthy()
    expect(screen.getAllByRole('link')).toHaveLength(3)
  })

  it('emits generate from the primary, and not while a brief is being written', async () => {
    const { emitted } = renderComposer()

    await fireEvent.click(screen.getByRole('button', { name: 'Generar brief' }))

    expect(emitted('generate')).toHaveLength(1)
    cleanup()
    renderComposer({ pending: true })
    expect(screen.getByRole('button', { name: 'Generar brief' }).hasAttribute('disabled')).toBe(
      true,
    )
  })

  it('warns when the recommendation advises against publishing', () => {
    renderComposer({
      opportunity: {
        ...base,
        recommendation: 'wait_for_case',
        recommendation_reason: 'Ninguna pieza muestra un caso real.',
      },
    })

    expect(screen.getByText('Esperar caso')).toBeTruthy()
    expect(screen.getByText('Ninguna pieza muestra un caso real.')).toBeTruthy()
  })
})
