import { describe, expect, it } from 'vitest'

import type { components } from '@/types/api'

import { hookRows, unclassifiedNote } from '@/lib/whyItWorked'

type HookLift = components['schemas']['HookLift']

function lift(overrides: Partial<HookLift> & Pick<HookLift, 'hook'>): HookLift {
  return {
    outliers_with: 1,
    outliers_total: 1,
    rest_with: 0,
    rest_total: 4,
    lift: null,
    observed_pattern: false,
    ...overrides,
  }
}

// Casos del run 46 (opp_1185, opp_1272, opp_911, opp_1335).
describe('hookRows', () => {
  it('pone primero el patrón observado y dice en cuántos outliers y piezas del resto aparece', () => {
    const rows = hookRows({
      hooks: [
        lift({ hook: 'counterintuitive', outliers_total: 4, rest_with: 2, lift: 0.5 }),
        lift({
          hook: 'news',
          outliers_with: 3,
          outliers_total: 4,
          rest_total: 4,
          observed_pattern: true,
        }),
      ],
      outliers_unclassified: 0,
    })

    expect(rows.map((row) => row.label)).toEqual(['Noticia', 'Algo contraintuitivo'])
    expect(rows[0]).toMatchObject({
      outliers: '3 de 4 outliers',
      rest: '0 de 4 del resto',
      comparison: 'ninguna pieza del resto lo usa',
      verdict: 'Patrón observado',
      observed: true,
    })
    expect(rows[1]).toMatchObject({ comparison: 'menos que en el resto', verdict: 'Anecdótico' })
  })

  it('da el lift con coma cuando el resto también usa el gancho', () => {
    const [row] = hookRows({
      hooks: [lift({ hook: 'question', rest_with: 1, rest_total: 7, lift: 7 })],
      outliers_unclassified: 0,
    })

    expect(row?.comparison).toBe('7,0× más que en el resto')
    expect(row?.rest).toBe('1 de 7 del resto')
  })

  it('no compara cuando el tema no tiene resto', () => {
    const [row] = hookRows({
      hooks: [lift({ hook: 'news', outliers_with: 2, outliers_total: 2, rest_total: 0 })],
      outliers_unclassified: 0,
    })

    expect(row?.rest).toBe('sin resto')
    expect(row?.comparison).toBe('sin piezas del resto con las que comparar')
  })

  it('muestra el gancho tal cual si no tiene etiqueta', () => {
    const [row] = hookRows({ hooks: [lift({ hook: 'meme' })], outliers_unclassified: 0 })

    expect(row?.label).toBe('meme')
  })
})

describe('unclassifiedNote', () => {
  it.each([
    { count: 0, expected: null },
    { count: 1, expected: '1 outlier sin gancho clasificado.' },
    { count: 3, expected: '3 outliers sin gancho clasificado.' },
  ])('$count → $expected', ({ count, expected }) => {
    expect(unclassifiedNote({ hooks: [], outliers_unclassified: count })).toBe(expected)
  })
})
