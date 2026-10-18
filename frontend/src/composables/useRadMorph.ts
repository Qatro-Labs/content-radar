import { usePreferredReducedMotion } from '@vueuse/core'

import { AGENT_TIMING } from '@/lib/agentMotion'

// Al reducir la barra, el ojo de Rad sale volando de su sitio en la barra hasta la esquina; al
// abrirla, vuelve. Es un único elemento (el ojo flotante) que se anima desde o hacia la marca de
// la barra, solo con `transform` y `opacity` (DESIGN.md §7). La barra se encoge o crece hacia la
// esquina a la vez.

const DOCK_MARK_SELECTOR = '[data-agent-dock] [data-rad-mark]'
const EASE_OUT = 'cubic-bezier(0.16, 1, 0.3, 1)'
const EASE_IN = 'cubic-bezier(0.4, 0, 1, 1)'
// La barra no desaparece de golpe: se encoge un poco hacia la esquina mientras se funde.
const DOCK_HIDDEN = { opacity: 0, transform: 'translateY(12px) scale(0.94)' }
const DOCK_SHOWN = { opacity: 1, transform: 'none' }

function centerOf(rect: DOMRect) {
  return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 }
}

// El transform que lleva el ojo flotante a la posición y el tamaño de la marca de la barra.
function onTopOf(eye: Element, mark: Element): string {
  const from = eye.getBoundingClientRect()
  const to = mark.getBoundingClientRect()
  const delta = { x: centerOf(to).x - centerOf(from).x, y: centerOf(to).y - centerOf(from).y }
  return `translate(${delta.x}px, ${delta.y}px) scale(${to.width / from.width})`
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

export function useRadMorph() {
  const motion = usePreferredReducedMotion()
  const animates = (element: Element) =>
    motion.value !== 'reduce' && typeof element.animate === 'function'

  function play(element: Element, keyframes: Keyframe[], options: KeyframeAnimationOptions) {
    return element.animate(keyframes, options).finished
  }

  // Reducir: el ojo sale de la barra (que se está yendo, pero sigue en el DOM) hacia la esquina.
  function onEyeEnter(eye: Element, done: () => void) {
    const mark = dockMark()
    if (!animates(eye) || mark === null) return done()
    const flight = { duration: AGENT_TIMING.eyeFlightMs, easing: EASE_OUT }
    void play(eye, [{ transform: onTopOf(eye, mark) }, { transform: 'none' }], flight).finally(done)
  }

  // Abrir: el ojo vuelve a su sitio en la barra; la marca de la barra espera a que llegue.
  function onEyeLeave(eye: Element, done: () => void) {
    const mark = dockMark()
    if (!animates(eye) || mark === null) return done()
    hide(mark)
    const flight = { duration: AGENT_TIMING.eyeFlightMs, easing: EASE_OUT }
    void play(eye, [{ transform: 'none' }, { transform: onTopOf(eye, mark) }], flight).finally(
      () => {
        reveal(mark)
        done()
      },
    )
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
