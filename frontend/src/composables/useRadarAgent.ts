import { createSharedComposable, useClipboard } from '@vueuse/core'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter, type RouteLocationRaw } from 'vue-router'

import { AgentRequestError, askAgent } from '@/api/agent'
import { USING_FIXTURES } from '@/api/opportunities'
import { AGENT_TIMING } from '@/lib/agentMotion'
import type { PlayableStep } from '@/lib/agentPlayer'
import {
  buildAgentQuestion,
  followUpSuggestions,
  MCP_DOCS_URL,
  suggestionsFor,
  viewContext,
} from '@/lib/agentRequest'
import {
  AGENT_ANCHOR,
  dataStepTarget,
  navigationRoute,
  navigationTargets,
  patchTarget,
  patchToQuery,
  screenOf,
} from '@/lib/agentTargets'
import type {
  AgentScreen,
  AgentStatus,
  AgentTarget,
  AgentTurnView,
  Navigation,
  RadarPatch,
} from '@/lib/agentTypes'
import { EXPLORE_TEXT_PARAM } from '@/lib/exploreView'
import { parseRadarQuery, serializeRadarQuery, type RadarQuery } from '@/lib/radarQuery'
import { RouteName } from '@/router/routeNames'

import { createAgentPlayback } from './agentPlayback'
import { useAgentPresence } from './useAgentPresence'
import { useRadarQuery } from './useRadarQuery'

const READING_LABEL = 'Leyendo la pregunta'
const WRITING_LABEL = 'Redactando la respuesta'
const COMPOSER_TARGET: AgentTarget = { anchor: AGENT_ANCHOR.composer, kind: 'block' }
const NEW_TAB = '_blank'
const NEW_TAB_FEATURES = 'noopener'

interface AgentRun {
  signal: AbortSignal
  dataSteps: number
}

function newTurn(id: number, question: string): AgentTurnView {
  return {
    id,
    question,
    status: 'running',
    steps: [],
    answer: null,
    visibleWords: 0,
    showEnding: false,
    summary: null,
    failure: null,
  }
}

function firstString(value: unknown): string | null {
  const first = Array.isArray(value) ? value[0] : value
  return typeof first === 'string' && first !== '' ? first : null
}

function radarParams(query: RadarQuery): string {
  return new URLSearchParams(serializeRadarQuery(query)).toString()
}

// D13 del plan fe-radar-agent: un solo estado para toda la pestaña. La conversación sobrevive a
// los cambios de pantalla que hace el propio agente y no se guarda en ningún sitio (regla 1).
export const useRadarAgent = createSharedComposable(() => {
  const route = useRoute()
  const router = useRouter()
  const radar = useRadarQuery()
  const presence = useAgentPresence()
  const { copy } = useClipboard()

  const turns = ref<AgentTurnView[]>([])
  const status = ref<AgentStatus>('idle')
  // Cada pregunta repite el barrido del radar en su primer paso de datos (DESIGN.md §7).
  const sweepCount = ref(0)
  // La última vista del Radar que dejó el agente: «Filtros puestos por Rad» si la URL sigue igual.
  const agentRadarParams = ref<string | null>(null)
  let nextTurnId = 1
  let controller: AbortController | null = null
  // Las navegaciones del agente no lo detienen; las de la persona, sí.
  let agentNavigations = 0

  const screen = computed(() => screenOf(route.name))
  const isAvailable = computed(() => !USING_FIXTURES && screen.value !== null)
  // El tema seleccionado en el Radar o abierto en el expediente.
  const openTopicId = computed(() => {
    if (screen.value === 'dossier') return firstString(route.params.id)
    return screen.value === 'radar' ? radar.query.value.selected : null
  })
  const view = computed(() =>
    viewContext(screen.value, {
      selected: radar.query.value.selected,
      dossierId: screen.value === 'dossier' ? openTopicId.value : null,
      search: firstString(route.query[EXPLORE_TEXT_PARAM]),
      radarQuery: radar.query.value,
    }),
  )
  const suggestions = computed(() =>
    turns.value.length === 0 ? suggestionsFor(view.value) : followUpSuggestions(view.value),
  )

  async function navigateAsAgent(to: RouteLocationRaw) {
    agentNavigations += 1
    try {
      await router.push(to)
    } finally {
      agentNavigations -= 1
    }
  }

  function mainBlockOf(currentScreen: AgentScreen | null): AgentTarget | null {
    if (currentScreen === null) return null
    const main = dataStepTarget(currentScreen)
    return presence.hasAnchor(main.anchor) ? main : null
  }

  // D8: si el objetivo no aparece, el bloque principal de la pantalla; si tampoco, sin presencia.
  async function goTo(target: AgentTarget, label: string, run: AgentRun) {
    const found = await presence.waitForAnchor(target.anchor, AGENT_TIMING.anchorWaitMs)
    if (run.signal.aborted) return null
    const reached = found ? target : mainBlockOf(screen.value)
    if (reached === null) {
      presence.hide()
      return null
    }
    await presence.moveTo(reached, label)
    return run.signal.aborted ? null : reached
  }

  // D3: un parche siempre se aplica en el Radar; desde otra pantalla, el agente vuelve a él con
  // ese estado. Fuera del Radar no hay controles del Radar a los que apuntar.
  async function patchStep(patch: RadarPatch, label: string, run: AgentRun) {
    const isOnRadar = screen.value === 'radar'
    const target = isOnRadar
      ? patchTarget(patch, { query: radar.query.value, hasAnchor: presence.hasAnchor })
      : mainBlockOf(screen.value)
    const reached = target === null ? null : await goTo(target, label, run)
    if (run.signal.aborted) return
    if (reached?.kind === 'control') presence.tap()
    const changes = patchToQuery(patch)
    const next = { ...(isOnRadar ? radar.query.value : parseRadarQuery({})), ...changes }
    if (isOnRadar) await radar.update(changes)
    else await navigateAsAgent({ name: RouteName.Discover, query: serializeRadarQuery(next) })
    agentRadarParams.value = radarParams(next)
  }

  async function navigateStep(nav: Navigation, label: string, run: AgentRun) {
    const { before, after } = navigationTargets(nav, {
      screen: screen.value,
      opportunityId: openTopicId.value,
      previewOpen: presence.hasAnchor(AGENT_ANCHOR.openDossier),
    })
    const pressed = before === null ? null : await goTo(before, label, run)
    if (run.signal.aborted) return
    if (pressed !== null) presence.tap()
    await navigateAsAgent(navigationRoute(nav))
    if (run.signal.aborted) return
    await goTo(after, label, run)
  }

  async function performStep(step: PlayableStep, run: AgentRun) {
    if (step.kind === 'data') {
      run.dataSteps += 1
      if (run.dataSteps === 1 && screen.value === 'radar') sweepCount.value += 1
    }
    if (step.action?.navigate) return navigateStep(step.action.navigate, step.label, run)
    if (step.action?.patch) return patchStep(step.action.patch, step.label, run)
    // Un paso de datos (o uno de vista que falló) señala el bloque principal de la pantalla.
    const main = screen.value === null ? null : dataStepTarget(screen.value)
    if (main !== null) await goTo(main, step.label, run)
  }

  function finishRun() {
    presence.hide()
    status.value = 'idle'
  }

  function playbackFor(turn: AgentTurnView, run: AgentRun) {
    return createAgentPlayback({
      turn,
      signal: run.signal,
      isReducedMotion: () => presence.isReducedMotion.value,
      performStep: (step) => performStep(step, run),
      onAnswerStart: () => {
        status.value = 'answering'
        void presence.moveTo(COMPOSER_TARGET, WRITING_LABEL)
      },
      onAnswerShown: presence.hide,
      onFinish: finishRun,
    })
  }

  async function ask(question: string): Promise<void> {
    const text = question.trim()
    if (text === '' || status.value !== 'idle') return
    const body = buildAgentQuestion(text, turns.value, view.value)
    turns.value.push(newTurn(nextTurnId++, text))
    const turn = turns.value.at(-1)!
    controller = new AbortController()
    const run: AgentRun = { signal: controller.signal, dataSteps: 0 }
    status.value = 'running'
    await presence.moveTo(COMPOSER_TARGET, READING_LABEL)
    const playback = playbackFor(turn, run)
    try {
      await askAgent(body, playback.push, run.signal)
    } catch (error) {
      if (run.signal.aborted) return
      if (error instanceof AgentRequestError) {
        turn.failure = error.message
        turn.status = 'failed'
      }
    }
    playback.end()
  }

  // Lo ya aplicado en la vista se queda; lo pendiente se descarta.
  function stop() {
    if (status.value === 'idle') return
    controller?.abort()
    const turn = turns.value.at(-1)
    if (turn?.status === 'running' || turn?.status === 'answering') turn.status = 'stopped'
    // Un paso cortado a medias no terminó: sin esto seguiría con el punto de «en curso».
    for (const step of turn?.steps ?? []) if (step.status === 'running') step.status = 'failed'
    finishRun()
  }

  function newConversation() {
    stop()
    turns.value = []
  }

  watch(
    () => route.name,
    () => {
      if (agentNavigations === 0) stop()
    },
    // Síncrono: se evalúa mientras la navegación del agente aún está en curso y la cuenta.
    { flush: 'sync' },
  )

  async function selectCited(id: string) {
    if (screen.value === 'radar') return radar.update({ selected: id })
    await router.push({ name: RouteName.Discover, query: { selected: id } })
  }

  function copyViewLink() {
    return copy(window.location.href)
  }

  function askFromAssistant(question: string) {
    void copy(question)
    window.open(MCP_DOCS_URL, NEW_TAB, NEW_TAB_FEATURES)
  }

  return {
    turns,
    status,
    presence: presence.presence,
    suggestions,
    sweepCount,
    agentRadarParams,
    isAvailable,
    ask,
    stop,
    newConversation,
    selectCited,
    copyViewLink,
    askFromAssistant,
  }
})
