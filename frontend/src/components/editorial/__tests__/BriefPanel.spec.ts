import { cleanup, fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, describe, expect, it } from 'vitest'

import fixture from '@fixtures/opportunities.json'
import type { components } from '@/types/api'

import BriefPanel, { BriefStage } from '../BriefPanel.vue'

type Schemas = components['schemas']

// TS lee los enums del JSON como `string`; el fixture cumple el contrato `OpportunityList`.
const base = (fixture.opportunities as Schemas['OpportunityList']).items[0]!

const OPTIONS = { platform: 'linkedin', goal: 'educate', format: 'post' } as const

function renderPanel(stage: BriefStage, opportunity: Schemas['Opportunity'] = base) {
  return render(BriefPanel, {
    props: {
      opportunity,
      stage,
      plainText: stage === BriefStage.Ready ? 'brief' : null,
      options: OPTIONS,
    },
  })
}

describe('BriefPanel', () => {
  // Sin `globals` de Vitest, Testing Library no desmonta solo entre tests.
  afterEach(cleanup)

  it('offers to generate while there is no brief for these options', async () => {
    const { emitted } = renderPanel(BriefStage.Idle)

    await fireEvent.click(screen.getByRole('button', { name: 'Generar brief' }))

    expect(emitted('generate')).toHaveLength(1)
    expect(screen.queryByRole('button', { name: 'Copiar enlace' })).toBeNull()
  })

  it('disables the primary while the brief is being written', () => {
    renderPanel(BriefStage.Pending)

    expect(screen.getByRole('button', { name: 'Generar brief' }).hasAttribute('disabled')).toBe(
      true,
    )
  })

  it('turns the primary into copying once the brief is ready', () => {
    renderPanel(BriefStage.Ready)

    expect(screen.getByRole('button', { name: 'Copiar brief' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Copiar enlace' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Generar brief' })).toBeNull()
  })

  it('writes the chosen option back without generating', async () => {
    const { emitted } = renderPanel(BriefStage.Idle)

    await fireEvent.click(screen.getByRole('button', { name: 'Carrusel' }))

    expect(emitted('update:options')).toEqual([[{ ...OPTIONS, format: 'carousel' }]])
    expect(emitted('generate')).toBeUndefined()
  })

  it('warns when the recommendation advises against publishing', () => {
    renderPanel(BriefStage.Idle, {
      ...base,
      recommendation: 'wait_for_case',
      recommendation_reason: 'Ninguna pieza muestra un caso real.',
    })

    expect(screen.getByText('Esperar caso')).toBeTruthy()
    expect(screen.getByText('Ninguna pieza muestra un caso real.')).toBeTruthy()
  })
})
