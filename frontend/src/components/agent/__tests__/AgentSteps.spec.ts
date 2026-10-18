import { fireEvent, render, screen, within } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import type { AgentStepView } from '@/lib/agentTypes'

import AgentSteps from '../AgentSteps.vue'

const STEPS: AgentStepView[] = [
  { id: 1, kind: 'data', label: 'Leyendo las oportunidades', status: 'done' },
  { id: 2, kind: 'view', label: 'Pulsando «Publicar ya»', status: 'done' },
  { id: 3, kind: 'data', label: 'Revisando «Agentes de IA en empresas»', status: 'done' },
  {
    id: 4,
    kind: 'view',
    label: 'Abriendo el expediente de «Agentes de IA en empresas»',
    status: 'done',
  },
  { id: 5, kind: 'data', label: 'Revisando qué no sabemos', status: 'done' },
  {
    id: 6,
    kind: 'view',
    label: 'Mostrando el encaje de «Agentes de IA en empresas»',
    status: 'done',
  },
]

describe('AgentSteps', () => {
  it('folds the finished steps into a summary line that opens them again', async () => {
    render(AgentSteps, {
      props: {
        steps: STEPS,
        summary: { steps: 6, data_steps: 3, view_steps: 3 },
        collapsible: true,
      },
    })

    const toggle = screen.getByRole('button', {
      name: 'Hizo 6 pasos: 3 de datos y 3 en la vista',
    })
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByRole('list')).toBeNull()

    await fireEvent.click(toggle)

    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    expect(within(screen.getByRole('list')).getByText('Leyendo las oportunidades')).toBeTruthy()
  })
})
