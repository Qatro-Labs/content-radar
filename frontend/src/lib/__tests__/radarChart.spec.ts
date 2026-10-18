import { describe, expect, it } from 'vitest'

import fixture from '@fixtures/opportunities.json'
import type { components } from '@/types/api'

import {
  buildRadarOption,
  sweepDelaySeconds,
  type RadarChartInput,
  type RadarChartOption,
  type RadarPalette,
} from '../radarChart'
import { buildRadarView } from '../radarView'

type OpportunityList = components['schemas']['OpportunityList']

// TS lee los enums del JSON como `string`; el fixture cumple el contrato `OpportunityList`.
const list = fixture.opportunities as OpportunityList

const { plotted } = buildRadarView(list, {
  lifecycle: [],
  confidence: null,
  topic: null,
  selected: null,
  highlight: [],
  gap: false,
  sort: 'opportunity',
  recommendation: null,
  tab: 'radar',
})

// Paleta fija con los colores de DESIGN.md §2; en la app se lee de las variables de main.css.
const PALETTE: RadarPalette = {
  stages: {
    emerging: { fill: '#3d7bff', stroke: '#3d7bff' },
    accelerating: { fill: '#b5e61d', stroke: '#6e8f00' },
    peaking: { fill: '#ff9a3c', stroke: '#e07a14' },
    saturated: { fill: '#f0565c', stroke: '#f0565c' },
    unknown: { fill: '#8a919c', stroke: '#8a919c' },
  },
  surface: '#ffffff',
  ink: '#121418',
  muted: '#626873',
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
    entering: false,
    ...patch,
  }
}

function seriesOfType(option: RadarChartOption, type: 'scatter' | 'effectScatter') {
  return [option.series].flat().find((series) => series?.type === type)
}

interface ItemSummary {
  name: string
  label: { show: boolean }
}

function itemsOf(option: RadarChartOption, type: 'scatter' | 'effectScatter') {
  return (seriesOfType(option, type)?.data ?? []) as ItemSummary[]
}

function labelledNames(option: RadarChartOption): string[] {
  return itemsOf(option, 'scatter')
    .filter((item) => item.label.show)
    .map((item) => item.name)
}

describe('buildRadarOption', () => {
  it('draws every bubble in the scatter series, also the growing ones', () => {
    const option = buildRadarOption(input())

    expect(itemsOf(option, 'scatter').map((item) => item.name)).toEqual([
      'opp_001',
      'opp_002',
      'opp_003',
      'opp_004',
    ])
  })

  it('rings only the growing bubbles that are not dimmed, with a silent transparent symbol', () => {
    // Crecen opp_001 (+86 %), opp_002 (+67 %) y opp_003 (+6 %); opp_004 cae (−30 %) y opp_002 se
    // atenúa. El anillo mide lo mismo que la burbuja: opp_001, seleccionada, 12 + 0,24 · 74 + 6 = 36.
    const option = buildRadarOption(input({ dimmedIds: new Set(['opp_002']) }))
    const rings = seriesOfType(option, 'effectScatter')

    expect(rings?.silent).toBe(true)
    expect(itemsOf(option, 'effectScatter').map((item) => item.name)).toEqual([
      'opp_001',
      'opp_003',
    ])
    expect(rings?.data).toContainEqual(
      expect.objectContaining({
        name: 'opp_001',
        symbolSize: 49,
        itemStyle: expect.objectContaining({ color: 'transparent' }),
      }),
    )
  })

  it('leaves the rings empty and hides every label while the sweep enters', () => {
    const option = buildRadarOption(input({ entering: true, selectedId: null }))

    expect(seriesOfType(option, 'effectScatter')?.data).toEqual([])
    expect(labelledNames(option)).toEqual([])
  })

  it('labels only the topics to publish now, and only without a selection', () => {
    // DESIGN.md §8 y D2 del plan fe-dashboard-v2. En el fixture solo opp_001 es «Publicar ya».
    expect(labelledNames(buildRadarOption(input({ selectedId: null })))).toEqual(['opp_001'])
    expect(labelledNames(buildRadarOption(input({ selectedId: 'opp_003' })))).toEqual([])
  })

  it('beats the rings at the pace of their acceleration once the sweep ends', () => {
    // DESIGN.md §7: +86 % → 2,0 s; +6 % → 3,6 s. La atenuada (opp_002) no late.
    const option = buildRadarOption(input({ dimmedIds: new Set(['opp_002']) }))

    expect(seriesOfType(option, 'effectScatter')?.data).toEqual([
      expect.objectContaining({
        name: 'opp_001',
        rippleEffect: expect.objectContaining({
          period: 2.0,
          color: PALETTE.stages.accelerating.stroke,
        }),
      }),
      expect.objectContaining({
        name: 'opp_003',
        rippleEffect: expect.objectContaining({
          period: 3.6,
          color: PALETTE.stages.peaking.stroke,
        }),
      }),
    ])
  })

  it('hides the bubble labels that overlap another label', () => {
    // Con datos reales (37 temas) las etiquetas se pisaban en el radar.
    const option = buildRadarOption(input())

    expect(seriesOfType(option, 'scatter')?.labelLayout).toEqual(
      expect.objectContaining({ hideOverlap: true }),
    )
  })

  it('delays the bubble entry only while the sweep enters', () => {
    // Con `LabelLayout`, ECharts funde cada etiqueta nueva con el `animationDelay` de su burbuja:
    // tras el barrido, las etiquetas tardaban 1,1–1,3 s más en salir.
    const entering = seriesOfType(buildRadarOption(input({ entering: true })), 'scatter')
    const settled = seriesOfType(buildRadarOption(input()), 'scatter')

    expect(entering?.animationDelay).toBeTypeOf('function')
    expect(settled?.animationDelay).toBe(0)
  })

  it('keeps a dimmed bubble in the scatter series, faded and without label', () => {
    // DESIGN.md §8: lo que no entra baja a 0,16 en su sitio, sin pasar a otra serie.
    const option = buildRadarOption(input({ dimmedIds: new Set(['opp_002']) }))

    expect(seriesOfType(option, 'scatter')?.data).toContainEqual(
      expect.objectContaining({
        name: 'opp_002',
        itemStyle: expect.objectContaining({ opacity: 0.16 }),
        label: expect.objectContaining({ show: false }),
      }),
    )
  })

  it('fades a bubble in place when it gets dimmed', () => {
    // ECharts 6.1 no anima la opacidad con `animationDurationUpdate`: sin la transición universal,
    // la burbuja salta a 0,16 en lugar de fundirse (G3, D14).
    const option = buildRadarOption(input())

    expect(seriesOfType(option, 'scatter')?.universalTransition).toBe(true)
  })

  it('drops the ring series and every animation with reduced motion', () => {
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
          color: PALETTE.surface,
          borderColor: PALETTE.stages.unknown.stroke,
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
