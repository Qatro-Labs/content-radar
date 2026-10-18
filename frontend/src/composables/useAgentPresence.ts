import {
  promiseTimeout,
  useEventListener,
  usePreferredReducedMotion,
  useResizeObserver,
} from '@vueuse/core'
import { computed, ref, shallowRef } from 'vue'

import {
  AGENT_TIMING,
  BLOCK_POINT_INSET,
  LABEL_FLIP_MARGIN_PX,
  RING_EXTRA_RADIUS_PX,
  RING_GAP_PX,
} from '@/lib/agentMotion'
import type { AgentTarget, PresenceView, RingBox } from '@/lib/agentTypes'

// La presencia es una capa absoluta sobre `[data-agent-root]` (DESIGN.md §7): todas las
// coordenadas son relativas a esa raíz.
const ROOT_SELECTOR = '[data-agent-root]'
const DOCK_SELECTOR = '[data-agent-dock]'
const ANCHOR_SELECTOR = '[data-agent]'
// Por encima de esta línea la cabecera tapa el objetivo; por debajo, hasta la barra del agente.
const VISIBLE_TOP_PX = 72
// De una sección más alta que el hueco basta con ver su parte de arriba, donde se posa la presencia.
const TALL_TARGET_VISIBLE_PX = 160

interface Box {
  left: number
  top: number
  width: number
  height: number
}

type Placement = Pick<PresenceView, 'x' | 'y' | 'ring' | 'labelOnLeft'>

const HIDDEN: PresenceView = {
  visible: false,
  x: 0,
  y: 0,
  label: '',
  ring: null,
  instant: true,
  tapCount: 0,
  labelOnLeft: false,
}

// Se compara el atributo en lugar de construir un selector: un id con comillas no lo rompe.
function findAnchor(anchor: string): HTMLElement | null {
  const candidates = document.querySelectorAll<HTMLElement>(ANCHOR_SELECTOR)
  return [...candidates].find((element) => element.dataset.agent === anchor) ?? null
}

function ringAround(target: AgentTarget, element: HTMLElement, box: Box): RingBox | null {
  if (target.kind === 'point') return null
  const gap = RING_GAP_PX[target.kind]
  const radius = Number.parseFloat(getComputedStyle(element).borderTopLeftRadius) || 0
  return {
    x: box.left - gap,
    y: box.top - gap,
    width: box.width + 2 * gap,
    height: box.height + 2 * gap,
    radius: radius + RING_EXTRA_RADIUS_PX,
  }
}

function measure(target: AgentTarget, element: HTMLElement, root: HTMLElement): Placement {
  const rect = element.getBoundingClientRect()
  const origin = root.getBoundingClientRect()
  const box = {
    left: rect.left - origin.left,
    top: rect.top - origin.top,
    width: rect.width,
    height: rect.height,
  }
  // Sobre una sección se posa arriba a la derecha para no tapar su contenido.
  const isBlock = target.kind === 'block'
  const x = isBlock ? box.left + box.width - BLOCK_POINT_INSET.right : box.left + box.width / 2
  const y = isBlock ? box.top + BLOCK_POINT_INSET.top : box.top + box.height / 2
  return {
    x,
    y,
    ring: ringAround(target, element, box),
    labelOnLeft: origin.width - x < LABEL_FLIP_MARGIN_PX,
  }
}

// La barra del agente es sticky: lo que queda debajo no se ve aunque esté dentro de la ventana.
// Lo que está dentro de la propia barra siempre se ve: no hace falta mover la página.
function scrollIntoGap(element: HTMLElement, behavior: ScrollBehavior) {
  if (element.closest(DOCK_SELECTOR) !== null) return
  const rect = element.getBoundingClientRect()
  const gapBottom = document.querySelector(DOCK_SELECTOR)?.getBoundingClientRect().top
  const bottom = gapBottom ?? window.innerHeight
  if (rect.height > bottom - VISIBLE_TOP_PX) {
    if (rect.top >= VISIBLE_TOP_PX && rect.top <= bottom - TALL_TARGET_VISIBLE_PX) return
    window.scrollTo({ top: window.scrollY + rect.top - VISIBLE_TOP_PX, behavior })
    return
  }
  if (rect.top >= VISIBLE_TOP_PX && rect.bottom <= bottom) return
  const gapCenter = (VISIBLE_TOP_PX + bottom) / 2
  window.scrollTo({ top: window.scrollY + rect.top + rect.height / 2 - gapCenter, behavior })
}

export function useAgentPresence() {
  const presence = ref<PresenceView>({ ...HIDDEN })
  const motionPreference = usePreferredReducedMotion()
  const isReducedMotion = computed(() => motionPreference.value === 'reduce')
  let current: AgentTarget | null = null
  let frame = 0
  const root = shallowRef<HTMLElement | null>(null)

  function hasAnchor(anchor: string): boolean {
    return findAnchor(anchor) !== null
  }

  // Primero llega, después actúa (DESIGN.md §7): resuelve cuando la presencia ya está en el
  // objetivo. Salta sin viajar la primera vez y con movimiento reducido.
  async function moveTo(target: AgentTarget, label: string): Promise<void> {
    const element = findAnchor(target.anchor)
    root.value = document.querySelector<HTMLElement>(ROOT_SELECTOR)
    if (element === null || root.value === null) return hide()
    const instant = isReducedMotion.value || !presence.value.visible
    scrollIntoGap(element, isReducedMotion.value ? 'auto' : 'smooth')
    current = target
    Object.assign(presence.value, measure(target, element, root.value), {
      visible: true,
      label,
      instant,
    })
    if (!instant) await promiseTimeout(AGENT_TIMING.travelMs)
  }

  // Tras navegar, la página nueva tarda en pintar sus secciones (el expediente carga datos).
  function waitForAnchor(anchor: string, timeoutMs: number): Promise<boolean> {
    return new Promise((resolve) => {
      let request = 0
      const timeout = setTimeout(() => {
        cancelAnimationFrame(request)
        resolve(hasAnchor(anchor))
      }, timeoutMs)
      const check = () => {
        if (!hasAnchor(anchor)) {
          request = requestAnimationFrame(check)
          return
        }
        clearTimeout(timeout)
        resolve(true)
      }
      check()
    })
  }

  function tap() {
    presence.value.tapCount += 1
  }

  function hide() {
    current = null
    Object.assign(presence.value, { visible: false, ring: null })
  }

  // La barra y el panel lateral son sticky: al hacer scroll el objetivo puede moverse respecto a
  // la raíz, así que se vuelve a medir.
  function remeasure() {
    cancelAnimationFrame(frame)
    frame = requestAnimationFrame(() => {
      const element = current === null ? null : findAnchor(current.anchor)
      if (current === null || element === null || root.value === null) return
      Object.assign(presence.value, measure(current, element, root.value))
    })
  }

  useEventListener(window, 'scroll', remeasure, { passive: true })
  useEventListener(window, 'resize', remeasure, { passive: true })
  // La transcripción crece dentro de la barra y la página cambia al cargar datos: el objetivo se
  // mueve sin scroll ni resize de la ventana.
  useResizeObserver(root, remeasure)

  return { presence, isReducedMotion, hasAnchor, moveTo, waitForAnchor, tap, hide, remeasure }
}
