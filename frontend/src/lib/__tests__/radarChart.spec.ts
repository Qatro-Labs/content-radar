import { describe, expect, it } from 'vitest'

import fixture from '@fixtures/opportunities.json'
import type { components } from '@/types/api'

import type { LifecyclePalette } from '../lifecycle'
import {
  buildRadarOption,
  sweepDelaySeconds,
  type RadarChartInput,
  type RadarChartOption,
} from '../radarChart'
import { buildRadarView } from '../radarView'

type OpportunityList = components['schemas']['OpportunityList']

// TS lee los enums del JSON como `string`; el fixture cumple el contrato `OpportunityList`.
const list = fixture.opportunities as OpportunityList

const { plotted } = buildRadarView(list, {
  period: '7d',
  lifecycle: [],
  confidence: null,
  topic: null,
  selected: null,
  highlight: [],
  gap: false,
  sort: 'opportunity',
})

// Paleta fija con los colores de DESIGN.md §2; en la app se lee de las variables --lc-*.
const PALETTE: LifecyclePalette = {
  emerging: { fill: '#3d7bff', stroke: '#3d7bff' },
  accelerating: { fill: '#b5e61d', stroke: '#6e8f00' },
  peaking: { fill: '#ff9a3c', stroke: '#e07a14' },
  saturated: { fill: '#f0565c', stroke: '#f0565c' },
  unknown: { fill: '#8a919c', stroke: '#8a919c' },
}

function input(patch: Partial<RadarChartInput> = {}): RadarChartInput {
  return {
    plotted,
    dimmedIds: new Set(),
    selectedId: 'opp_001',
    hoveredId: null,
    palette: PALETTE,
    reducedMotion: false,
    showLabels: true,
    ...patch,
  }
}

function seriesOfType(option: RadarChartOption, type: 'scatter' | 'effectScatter') {
  return [option.series].flat().find((series) => series?.type === type)
}

describe('buildRadarOption', () => {
  it('beats a growing bubble that is not dimmed, at the pace of its acceleration', () => {
    // opp_001 acelera +86 %: la tabla de DESIGN.md §7 le da un latido de 2,0 s.
    const option = buildRadarOption(input())

    expect(seriesOfType(option, 'effectScatter')?.data).toContainEqual(
      expect.objectContaining({
        name: 'opp_001',
        rippleEffect: expect.objectContaining({ period: 2.0, color: '#6e8f00' }),
      }),
    )
    expect(seriesOfType(option, 'scatter')?.data).not.toContainEqual(
      expect.objectContaining({ name: 'opp_001' }),
    )
  })

  it('draws a dimmed bubble still, faded and without label', () => {
    // opp_002 crece (+67 %), pero atenuada pierde el latido y la etiqueta (DESIGN.md §8).
    const option = buildRadarOption(input({ dimmedIds: new Set(['opp_002']) }))

    expect(seriesOfType(option, 'scatter')?.data).toContainEqual(
      expect.objectContaining({
        name: 'opp_002',
        itemStyle: expect.objectContaining({ opacity: 0.16 }),
        label: expect.objectContaining({ show: false }),
      }),
    )
    expect(seriesOfType(option, 'effectScatter')?.data).not.toContainEqual(
      expect.objectContaining({ name: 'opp_002' }),
    )
  })

  it('drops the pulse series and every animation with reduced motion', () => {
    const option = buildRadarOption(input({ reducedMotion: true }))

    expect(seriesOfType(option, 'effectScatter')).toBeUndefined()
    expect(option.animation).toBe(false)
  })

  it('draws a topic without stage hollow, with a dashed border', () => {
    const withoutStage = plotted.map((opportunity) =>
      opportunity.id === 'opp_002'
        ? { ...opportunity, lifecycle: 'unknown' as const }
        : opportunity,
    )

    const option = buildRadarOption(input({ plotted: withoutStage }))

    expect(seriesOfType(option, 'scatter')?.data).toContainEqual(
      expect.objectContaining({
        name: 'opp_002',
        itemStyle: expect.objectContaining({
          color: '#ffffff',
          borderColor: '#8a919c',
          borderType: 'dashed',
        }),
      }),
    )
  })
})

describe('sweepDelaySeconds', () => {
  it.each([
    { name: 'the "Prioridad" corner, where the beam pivots', fit: 100, momentum: 100, at: 0.35 },
    { name: 'the opposite corner (φ ≈ 60.64°)', fit: 0, momentum: 0, at: 1.26 },
  ])('detects $name at $at s', ({ fit, momentum, at }) => {
    expect(sweepDelaySeconds(fit, momentum)).toBeCloseTo(at, 2)
  })
})
