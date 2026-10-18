import { describe, expect, it } from 'vitest'

import { isDescending, topicStageStyle } from '@/lib/lifecycle'

// Casos del run 46: la regla tiene que coincidir con los `lifecycle_reason` que empiezan por
// «En descenso:» (19 de 54 temas, sin excepciones).
describe('isDescending', () => {
  it.each([
    {
      name: 'sin etapa, con datos y bajando',
      lifecycle: 'unknown',
      growth_status: 'observed',
      acceleration: -0.4,
      expected: true,
    },
    {
      name: 'sin etapa, ventana anterior vacía y bajando',
      lifecycle: 'unknown',
      growth_status: 'estimated',
      acceleration: -0.1,
      expected: true,
    },
    {
      name: 'datos insuficientes',
      lifecycle: 'unknown',
      growth_status: 'preliminary',
      acceleration: -0.6,
      expected: false,
    },
    {
      name: 'sin etapa y subiendo',
      lifecycle: 'unknown',
      growth_status: 'observed',
      acceleration: 0.3,
      expected: false,
    },
    {
      name: 'saturado y bajando',
      lifecycle: 'saturated',
      growth_status: 'observed',
      acceleration: -0.2,
      expected: false,
    },
  ] as const)('$name', ({ expected, ...topic }) => {
    expect(isDescending(topic)).toBe(expected)
  })
})

describe('topicStageStyle', () => {
  it('rotula «En descenso» con el color y el trazo de sin etapa', () => {
    const style = topicStageStyle({
      lifecycle: 'unknown',
      growth_status: 'observed',
      acceleration: -0.4,
    })

    expect(style.label).toBe('En descenso')
    expect(style.dashed).toBe(true)
    expect(style.cssVar.fill).toBe('--lc-unknown')
  })

  it('deja «Sin tendencia clara» cuando faltan datos', () => {
    const style = topicStageStyle({
      lifecycle: 'unknown',
      growth_status: 'preliminary',
      acceleration: -0.4,
    })

    expect(style.label).toBe('Sin tendencia clara')
  })
})
