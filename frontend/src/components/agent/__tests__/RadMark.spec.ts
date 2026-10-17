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

  it('looks straight ahead when there is nothing to look at', () => {
    render(RadMark, { props: { state: RESTING } })

    expect(screen.getByTestId('rad-gaze').style.transform).toBe('translate(0px, 0px)')
  })

  it('looks toward the presence, 3.2 viewBox units from the centre', async () => {
    // Raíz de la app en (0, 0) y marca de 40 px en (10, 10): su centro es (30, 30). La presencia
    // está 100 px a la derecha, en la misma altura.
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (
      this: HTMLElement,
    ) {
      return this.hasAttribute('data-agent-root') ? box(0, 0, 1000) : box(10, 10, 40)
    })
    const state: RadMarkState = { ...RESTING, lookAt: { x: 130, y: 30 } }
    const App = defineComponent({
      render: () => h('div', { 'data-agent-root': '' }, [h(RadMark, { state })]),
    })

    render(App)
    await nextTick()

    expect(screen.getByTestId('rad-gaze').style.transform).toBe('translate(3.2px, 0px)')
  })
})
