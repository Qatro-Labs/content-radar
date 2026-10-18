import { cleanup, render, screen } from '@testing-library/vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'

import RadMark, { type RadMarkState } from '../RadMark.vue'

const RESTING: RadMarkState = { working: false, scanKey: 0, blinkKey: 0, lookAt: null }

function box(left: number, top: number, size: number): DOMRect {
  return { left, top, width: size, height: size } as DOMRect
}

// Sin `globals` de Vitest, Testing Library no desmonta solo entre tests.
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('RadMark', () => {
  it('shows the pupil at rest and hides it while Rad works', async () => {
    const { rerender } = render(RadMark, { props: { state: RESTING } })
    expect(screen.getByTestId('rad-pupil').style.opacity).toBe('1')

    await rerender({ state: { ...RESTING, working: true } })

    expect(screen.getByTestId('rad-pupil').style.opacity).toBe('0')
  })

  it('keeps the beam sweeping while asked to, and stops it when Rad stops working', async () => {
    const { container, rerender } = render(RadMark, {
      props: { state: { ...RESTING, working: true, sweeping: true } },
    })
    expect(container.querySelector('.rad-sweep-loop')).not.toBeNull()

    await rerender({ state: { ...RESTING, sweeping: true } })

    expect(container.querySelector('.rad-sweep-loop')).toBeNull()
  })

  it('looks straight ahead when there is nothing to look at', () => {
    render(RadMark, { props: { state: RESTING } })

    expect(screen.getByTestId('rad-gaze').style.transform).toBe('translate(0px, 0px)')
  })

  // Raíz de la app en (0, 0) y marca de 40 px en (10, 10): su centro es (30, 30). Lo que mira está a
  // la derecha, a la misma altura: lejos mira hasta el borde (3,2 unidades del viewBox); cerca, menos,
  // como un ojo de verdad.
  it.each([
    { case: 'far away, to the edge', dx: 400, transform: 'translate(3.2px, 0px)' },
    { case: 'close by, half way', dx: 80, transform: 'translate(1.6px, 0px)' },
  ])('looks toward what it follows: $case', async ({ dx, transform }) => {
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (
      this: HTMLElement,
    ) {
      return this.hasAttribute('data-agent-root') ? box(0, 0, 1000) : box(10, 10, 40)
    })
    const state: RadMarkState = { ...RESTING, lookAt: { x: 30 + dx, y: 30 } }
    const App = defineComponent({
      render: () => h('div', { 'data-agent-root': '' }, [h(RadMark, { state })]),
    })

    render(App)
    await nextTick()

    expect(screen.getByTestId('rad-gaze').style.transform).toBe(transform)
  })

  it('keeps the iris centred while it works as a radar, whatever it follows', async () => {
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (
      this: HTMLElement,
    ) {
      return this.hasAttribute('data-agent-root') ? box(0, 0, 1000) : box(10, 10, 40)
    })
    const state: RadMarkState = { ...RESTING, working: true, lookAt: { x: 430, y: 30 } }
    const App = defineComponent({
      render: () => h('div', { 'data-agent-root': '' }, [h(RadMark, { state })]),
    })

    render(App)
    await nextTick()

    expect(screen.getByTestId('rad-gaze').style.transform).toBe('translate(0px, 0px)')
  })
})
