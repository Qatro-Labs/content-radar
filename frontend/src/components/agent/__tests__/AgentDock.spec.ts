import { cleanup, fireEvent, render, screen, within } from '@testing-library/vue'
import { afterEach, describe, expect, it } from 'vitest'

import type { AgentStatus, AgentTurnView, AnswerEvent, CitedOpportunity } from '@/lib/agentTypes'

import AgentDock from '../AgentDock.vue'
import type { RadMarkState } from '../RadMark.vue'

const QUESTION = '¿Qué conviene publicar esta semana?'
const FAILURE = 'Se cortó la conexión con el agente. Lo que ya cambió en la vista se queda'
const MARK: RadMarkState = { working: false, scanKey: 0, blinkKey: 0, lookAt: null }

const AGENTS: CitedOpportunity = {
  id: 'opp_1',
  topic: 'Agentes de IA en empresas',
  lifecycle: 'accelerating',
  opportunity_score: 82,
}
const EVALS: CitedOpportunity = {
  id: 'opp_2',
  topic: 'Evaluación de agentes',
  lifecycle: 'emerging',
  opportunity_score: 74,
}
const VOICE: CitedOpportunity = {
  id: 'opp_3',
  topic: 'Voz en atención al cliente',
  lifecycle: 'peaking',
  opportunity_score: 61,
}

function answerCiting(cited: CitedOpportunity[]): AnswerEvent {
  return {
    text: 'Agentes de IA en empresas encabeza la semana.',
    cited,
    unknowns: ['No sabemos cuántos directivos lo leen.'],
  }
}

function turn(overrides: Partial<AgentTurnView> = {}): AgentTurnView {
  return {
    id: 1,
    question: QUESTION,
    status: 'done',
    steps: [],
    answer: answerCiting([AGENTS, EVALS]),
    visibleWords: 7,
    showEnding: true,
    summary: { steps: 2, data_steps: 1, view_steps: 1 },
    failure: null,
    ...overrides,
  }
}

function renderDock(props: { turns: AgentTurnView[]; status: AgentStatus }) {
  return render(AgentDock, { props: { suggestions: [], mark: MARK, ...props } })
}

const questionHeading = () => screen.queryByRole('heading', { name: QUESTION })
const foldRow = () => screen.getByText('Rad respondió').parentElement!

async function openAnswer() {
  await fireEvent.click(screen.getByRole('button', { name: 'Ver respuesta' }))
}

// Sin `globals` de Vitest, Testing Library no desmonta solo entre tests.
afterEach(cleanup)

describe('AgentDock', () => {
  it('folds the answer into one row when Rad finishes, and opens it again', async () => {
    const { rerender } = renderDock({
      turns: [turn({ status: 'answering', showEnding: false, summary: null })],
      status: 'answering',
    })
    expect(questionHeading()).not.toBeNull()
    expect(screen.queryByText('Rad respondió')).toBeNull()

    await rerender({ turns: [turn()], status: 'idle' })

    expect(questionHeading()).toBeNull()
    const toggle = screen.getByRole('button', { name: 'Ver respuesta' })
    expect(toggle.getAttribute('aria-expanded')).toBe('false')

    await fireEvent.click(toggle)

    expect(questionHeading()).not.toBeNull()
    expect(toggle.textContent).toContain('Ocultar respuesta')
    expect(toggle.getAttribute('aria-expanded')).toBe('true')
    expect(document.getElementById(toggle.getAttribute('aria-controls') ?? '')).not.toBeNull()
  })

  // El stream se puede cortar con la respuesta ya escrita: el turno tiene respuesta y aun así falló.
  it('keeps a failed turn open so its error stays visible, even after choosing a topic', async () => {
    const answering = turn({ status: 'answering', summary: null })
    const { rerender } = renderDock({ turns: [answering], status: 'answering' })

    await rerender({
      turns: [{ ...answering, status: 'failed', failure: FAILURE }],
      status: 'idle',
    })

    expect(questionHeading()).not.toBeNull()
    expect(screen.getByText(FAILURE)).toBeTruthy()
    expect(screen.queryByText('Rad respondió')).toBeNull()

    // Sin fila plegada no habría cómo volver a abrirla.
    await fireEvent.click(screen.getByRole('button', { name: /Agentes de IA en empresas/ }))

    expect(screen.getByText(FAILURE)).toBeTruthy()
  })

  it.each([
    { case: 'one', cited: [AGENTS], text: '· 1 tema citado' },
    { case: 'several', cited: [AGENTS, EVALS, VOICE], text: '· 3 temas citados' },
  ])('sums up the folded answer with the question and $case cited topic(s)', ({ cited, text }) => {
    renderDock({ turns: [turn({ answer: answerCiting(cited) })], status: 'idle' })

    expect(within(foldRow()).getByText(QUESTION)).toBeTruthy()
    expect(within(foldRow()).getByText(text)).toBeTruthy()
  })

  it('leaves the count out of the folded answer when it cites no topic', () => {
    renderDock({ turns: [turn({ answer: answerCiting([]) })], status: 'idle' })

    expect(within(foldRow()).getByText(QUESTION)).toBeTruthy()
    expect(within(foldRow()).queryByText(/citad/)).toBeNull()
  })

  it('peeks at a cited topic on hover or focus, and lets go on leave, blur or Escape', async () => {
    const { emitted } = renderDock({ turns: [turn()], status: 'idle' })
    await openAnswer()
    const dock = screen.getByRole('region', { name: 'Rad, el agente del Radar' })
    const chip = screen.getByRole('button', { name: /Agentes de IA en empresas/ })

    await fireEvent.mouseEnter(chip)
    expect(dock.hasAttribute('data-peeking')).toBe(true)
    await fireEvent.mouseLeave(chip)
    expect(dock.hasAttribute('data-peeking')).toBe(false)
    await fireEvent.focus(chip)
    await fireEvent.blur(chip)
    await fireEvent.mouseEnter(chip)
    await fireEvent.keyDown(window, { key: 'Escape' })

    expect(emitted('peekCited')).toEqual([['opp_1'], [null], ['opp_1'], [null], ['opp_1'], [null]])
  })

  it('selects a cited topic and folds the answer so the page shows it', async () => {
    const { emitted } = renderDock({ turns: [turn()], status: 'idle' })
    await openAnswer()
    const chip = screen.getByRole('button', { name: /Evaluación de agentes/ })

    await fireEvent.mouseEnter(chip)
    await fireEvent.click(chip)

    expect(emitted('selectCited')).toEqual([['opp_2']])
    expect(emitted('peekCited')).toEqual([['opp_2'], [null]])
    expect(questionHeading()).toBeNull()
    expect(screen.getByRole('button', { name: 'Ver respuesta' })).toBeTruthy()
  })

  it.each([
    { case: 'next to the field, before any question', turns: [] },
    { case: 'in the header, with a conversation', turns: [turn()] },
  ])('minimizes to the eye from «Minimizar Rad»: $case', async ({ turns }) => {
    const { emitted } = renderDock({ turns, status: 'idle' })

    await fireEvent.click(screen.getByRole('button', { name: 'Minimizar Rad' }))

    expect(emitted('minimize')).toHaveLength(1)
  })
})
