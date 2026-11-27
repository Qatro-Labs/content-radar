import { describe, expect, it } from 'vitest'

import { ratioLabel } from '@/lib/evidenceFormat'
import { EXPLORE_FILTER_LABEL } from '@/lib/exploreView'
import { GROWTH_HELP, HELP, RECOMMENDATION_HELP, SCORE_COMPONENT_HELP } from '@/lib/helpText'
import { LIFECYCLE_STYLE } from '@/lib/lifecycle'
import { RECOMMENDATION_LABEL, latamGapLabel } from '@/lib/opportunityFormat'
import type { components } from '@/types/api'

type Evidence = components['schemas']['Evidence']

describe('plain language', () => {
  it('no user-facing label map contains internal jargon', () => {
    const visible = [
      ...Object.values(RECOMMENDATION_LABEL),
      ...Object.values(LIFECYCLE_STYLE).map((style) => style.label),
      latamGapLabel(true),
      latamGapLabel(false),
      latamGapLabel(null),
      ...Object.values(RECOMMENDATION_HELP),
      ...Object.values(GROWTH_HELP),
      ...Object.values(HELP),
      ...Object.values(SCORE_COMPONENT_HELP),
    ].join(' ')
    expect(visible).not.toMatch(/outlier|momentum|LATAM|Emergente|Saturado|En pico|independientes/i)
  })

  it('uses the exact labels from the spec table', () => {
    expect(RECOMMENDATION_LABEL.wait_for_case).toBe('Esperar un caso real')
    expect(LIFECYCLE_STYLE.emerging.label).toBe('Empieza a crecer')
    expect(LIFECYCLE_STYLE.accelerating.label).toBe('Crece rápido')
    expect(LIFECYCLE_STYLE.peaking.label).toBe('En su punto alto')
    expect(LIFECYCLE_STYLE.saturated.label).toBe('Ya muy cubierto')
    expect(ratioLabel({ is_outlier: true, outlier_ratio: 5 } as Evidence)).toBe('Rinde 3× o más')
    expect(EXPLORE_FILTER_LABEL.outliers).toBe('Rinden 3× o más')
    expect(latamGapLabel(true)).toBe('casi nadie lo cuenta en Latinoamérica')
    expect(latamGapLabel(false)).toBe('ya se cuenta mucho en Latinoamérica')
    expect(latamGapLabel(null)).toBe('cobertura en Latinoamérica no disponible')
  })
})
