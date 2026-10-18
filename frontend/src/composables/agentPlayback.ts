import { promiseTimeout } from '@vueuse/core'

import { AGENT_TIMING } from '@/lib/agentMotion'
import { takePlayable, type Playable, type PlayableStep } from '@/lib/agentPlayer'
import type { AgentStreamEvent, AgentTurnView, AnswerEvent } from '@/lib/agentTypes'
import { countWords } from '@/lib/answerWords'

// D7 del plan fe-radar-agent: el ritmo de un turno. Los eventos se guardan en un búfer y se
// reproducen de uno en uno: cada paso dura al menos `stepMs` y la respuesta espera a que la cola
// se vacíe. Lo que hace cada paso en la página lo decide `performStep`.

const CONNECTION_LOST_MESSAGE =
  'Se cortó la conexión con el agente. Lo que ya cambió en la vista se queda'
const STEP_FAILED_MESSAGE = 'Rad no pudo terminar este paso. Lo que ya cambió en la vista se queda.'

export interface PlaybackHost {
  // El turno reactivo que pinta la barra.
  turn: AgentTurnView
  // Se aborta con «Detener»: cada espera lo comprueba antes de seguir.
  signal: AbortSignal
  isReducedMotion: () => boolean
  // Lleva la presencia al objetivo del paso y aplica su acción.
  performStep: (step: PlayableStep) => Promise<void>
  onAnswerStart: () => void
  onAnswerShown: () => void
  onFinish: () => void
}

export interface AgentPlayback {
  push: (event: AgentStreamEvent) => void
  // El stream se cerró: lo pendiente se reproduce y el turno termina.
  end: () => void
}

export function createAgentPlayback(host: PlaybackHost): AgentPlayback {
  const { turn, signal } = host
  let buffer: AgentStreamEvent[] = []
  let streamEnded = false
  let isPumping = false
  let isFinished = false

  signal.addEventListener('abort', () => {
    buffer = []
  })

  async function playStep(step: PlayableStep) {
    const minimum = promiseTimeout(
      host.isReducedMotion() ? AGENT_TIMING.reducedStepMs : AGENT_TIMING.stepMs,
    )
    turn.steps.push({ id: step.id, kind: step.kind, label: step.label, status: 'running' })
    const row = turn.steps.at(-1)
    await host.performStep(step)
    if (signal.aborted || row === undefined) return
    row.status = step.status
    await minimum
  }

  async function playAnswer(answer: AnswerEvent) {
    host.onAnswerStart()
    turn.status = 'answering'
    turn.answer = answer
    const total = countWords(answer.text)
    if (host.isReducedMotion()) turn.visibleWords = total
    while (turn.visibleWords < total) {
      await promiseTimeout(AGENT_TIMING.wordMs)
      if (signal.aborted) return
      turn.visibleWords += 1
    }
    turn.showEnding = true
    host.onAnswerShown()
  }

  async function play(playable: Playable) {
    if (playable.type === 'step') return playStep(playable.step)
    if (playable.type === 'answer') return playAnswer(playable.answer)
    if (playable.type === 'error') {
      turn.failure = playable.error.message
      turn.status = 'failed'
      return
    }
    turn.summary = playable.summary
    if (turn.status !== 'failed') turn.status = 'done'
  }

  async function playInOrder(ready: Playable[]) {
    for (const playable of ready) {
      if (signal.aborted) return
      await play(playable)
    }
  }

  // Sin `done`, el stream se cortó: lo ya aplicado en la vista se queda.
  function finish() {
    if (isFinished || signal.aborted) return
    isFinished = true
    if (turn.summary === null && turn.status !== 'failed') {
      turn.failure = CONNECTION_LOST_MESSAGE
      turn.status = 'failed'
    }
    host.onFinish()
  }

  // Un paso que la página no pudo hacer (p. ej. no cargó la pantalla a la que iba) corta el turno:
  // sin esto se quedaría «en curso». Lo que siga llegando del stream se descarta. Tras «Detener»,
  // el turno ya está parado y no se pinta como fallido.
  function failTurn() {
    buffer = []
    if (signal.aborted) return
    for (const row of turn.steps) if (row.status === 'running') row.status = 'failed'
    turn.failure = STEP_FAILED_MESSAGE
    turn.status = 'failed'
    finish()
  }

  async function playBuffered() {
    for (;;) {
      const { ready, rest } = takePlayable(buffer, streamEnded)
      buffer = rest
      if (ready.length === 0 || signal.aborted) return
      await playInOrder(ready)
    }
  }

  async function pump() {
    if (isPumping || isFinished) return
    isPumping = true
    try {
      await playBuffered()
    } catch {
      failTurn()
      return
    } finally {
      isPumping = false
    }
    if (streamEnded && buffer.length === 0) finish()
  }

  return {
    push(event) {
      if (signal.aborted || isFinished) return
      buffer.push(event)
      void pump()
    },
    end() {
      streamEnded = true
      void pump()
    },
  }
}
