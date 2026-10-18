import { usePreferredReducedMotion } from '@vueuse/core'

import { AGENT_TIMING } from '@/lib/agentMotion'

// Al reducir la barra, el ojo de Rad vuela de su sitio en la barra hasta la esquina; al abrirla,
// vuelve. Es un único elemento (el ojo flotante) que se anima desde o hacia la marca de la barra,
// en línea recta y sin pausas, solo con `transform` y `opacity` (DESIGN.md §7), y parpadea al llegar.

const DOCK_MARK_SELECTOR = '[data-agent-dock] [data-rad-mark]'
const EASE_OUT = 'cubic-bezier(0.16, 1, 0.3, 1)'
const EASE_IN = 'cubic-bezier(0.4, 0, 1, 1)'
// La barra no desaparece de golpe: se encoge un poco hacia la esquina mientras se funde.
const DOCK_HIDDEN = { opacity: 0, transform: 'translateY(12px) scale(0.94)' }
const DOCK_SHOWN = { opacity: 1, transform: 'none' }

interface Offset {
  dx: number
  dy: number
  scale: number
}

const HOME: Offset = { dx: 0, dy: 0, scale: 1 }

function centerOf(rect: DOMRect) {
  return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 }
}

// Lo que hay que mover y escalar el ojo flotante para ponerlo encima de la marca de la barra.
function offsetToMark(eye: Element, mark: Element): Offset {
  const from = eye.getBoundingClientRect()
  const to = mark.getBoundingClientRect()
  return {
    dx: centerOf(to).x - centerOf(from).x,
    dy: centerOf(to).y - centerOf(from).y,
    scale: to.width / from.width,
  }
}

function transformAt({ dx, dy, scale }: Offset): string {
  return `translate(${dx}px, ${dy}px) scale(${scale})`
}

function flightBetween(from: Offset, to: Offset): Keyframe[] {
  return [{ transform: transformAt(from) }, { transform: transformAt(to) }]
}

function dockMark(): HTMLElement | null {
  return document.querySelector<HTMLElement>(DOCK_MARK_SELECTOR)
}

function hide(element: HTMLElement | null) {
  if (element) element.style.opacity = '0'
}

function reveal(element: HTMLElement | null) {
  if (element) element.style.opacity = ''
}

export function useRadMorph({ onLanded }: { onLanded?: () => void } = {}) {
  const motion = usePreferredReducedMotion()
  const animates = (element: Element) =>
    motion.value !== 'reduce' && typeof element.animate === 'function'

  function play(element: Element, keyframes: Keyframe[], options: KeyframeAnimationOptions) {
    return element.animate(keyframes, options).finished
  }

  const flight = { duration: AGENT_TIMING.eyeFlightMs, easing: EASE_OUT }

  // Reducir: el ojo sale de la barra (que se está yendo, pero sigue en el DOM) hacia la esquina.
  function onEyeEnter(eye: Element, done: () => void) {
    const mark = dockMark()
    if (!animates(eye) || mark === null) return done()
    void play(eye, flightBetween(offsetToMark(eye, mark), HOME), flight).finally(() => {
      done()
      onLanded?.()
    })
  }

  // Abrir: el ojo vuelve a su sitio en la barra; la marca de la barra espera a que llegue.
  function onEyeLeave(eye: Element, done: () => void) {
    const mark = dockMark()
    if (!animates(eye) || mark === null) return done()
    hide(mark)
    void play(eye, flightBetween(HOME, offsetToMark(eye, mark)), flight).finally(() => {
      reveal(mark)
      done()
      onLanded?.()
    })
  }

  // Al volver, la barra solo se funde: si también se moviera, la marca a la que vuela el ojo se
  // desplazaría durante el vuelo y el ojo aterrizaría fuera de su sitio.
  function onDockEnter(dock: Element, done: () => void) {
    if (!animates(dock)) return done()
    const options = { duration: AGENT_TIMING.dockInMs, easing: EASE_OUT }
    void play(dock, [{ opacity: 0 }, { opacity: 1 }], options).finally(done)
  }

  // Su marca se oculta al instante: desde ahí sale volando el ojo.
  function onDockLeave(dock: Element, done: () => void) {
    hide(dock.querySelector<HTMLElement>('[data-rad-mark]'))
    if (!animates(dock)) return done()
    const options = { duration: AGENT_TIMING.dockOutMs, easing: EASE_IN }
    void play(dock, [DOCK_SHOWN, DOCK_HIDDEN], options).finally(done)
  }

  return { onEyeEnter, onEyeLeave, onDockEnter, onDockLeave }
}
