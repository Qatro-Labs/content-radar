import type { EffectScatterSeriesOption, ScatterSeriesOption } from 'echarts/charts'
import type { GridComponentOption } from 'echarts/components'
import type { ComposeOption } from 'echarts/core'

import { LIFECYCLE_STYLE, type LifecyclePalette } from './lifecycle'
import { bubbleSize, pulsePeriodSeconds, SCORE_MAX } from './opportunityFormat'
import type { RankedOpportunity } from './radarView'

export type RadarChartOption = ComposeOption<
  ScatterSeriesOption | EffectScatterSeriesOption | GridComponentOption
>

export interface RadarChartInput {
  plotted: RankedOpportunity[]
  dimmedIds: Set<string>
  selectedId: string | null
  hoveredId: string | null
  palette: LifecyclePalette
  reducedMotion: boolean
  showLabels: boolean
}

export interface PlotSize {
  width: number
  height: number
}

export interface PlotPoint {
  x: number
  y: number
}

// El área del radar es 16:9 (DESIGN.md §6); el ángulo con el que el haz detecta cada burbuja
// usa esa proporción.
export const RADAR_ASPECT: PlotSize = { width: 16, height: 9 }

// DESIGN.md §7: el haz pivota en la esquina "Prioridad" de 170° a 290°, en 1,8 s tras 0,2 s.
// RadarSweep.vue anima con estos mismos valores para que cada burbuja aparezca cuando el haz pasa.
export const SWEEP = { delayMs: 200, durationMs: 1800, fromDeg: 170, toDeg: 290 }
// Desde la esquina, 180° apunta hacia abajo: el haz arranca 10° antes de la vertical.
const BEAM_DOWN_DEG = 180
const DEGREES_PER_RADIAN = 180 / Math.PI
const MS_PER_SECOND = 1000

// DESIGN.md §8: la seleccionada mide 6 px más; §7: el hover escala la burbuja a 1,12.
export const SELECTED_EXTRA_PX = 6
const HOVER_SCALE = 1.12
// DESIGN.md §8: lo que no entra en el filtro o el resaltado baja a esta opacidad.
const DIMMED_OPACITY = 0.16
// DESIGN.md §7: aparición de 480 ms con rebote; atenuar y seleccionar, 320 ms con la curva de la UI
// (`exponentialOut` es la misma cubic-bezier(0.16, 1, 0.3, 1)).
const ENTRY_DURATION_MS = 480
const UPDATE_DURATION_MS = 320
// D9 del plan fe-radar-view: un anillo que crece hasta 2,4 veces la burbuja.
const PULSE_RIPPLE = { brushType: 'stroke', scale: 2.4, number: 1 } as const

// ECharts pinta en canvas y no lee `var(--…)`: blanco, Tinta y Apagado de DESIGN.md §2.
const WHITE = '#ffffff'
const INK = '#121418'
const MUTED = '#626873'
// Borde blanco de 2 px (DESIGN.md §8); "Sin etapa", hueca con trazo discontinuo (artboard E).
const BUBBLE_BORDER_PX = 2
const HOLLOW_BORDER_PX = 1.5
// El nombre con el que @fontsource-variable/geist registra la fuente (main.css usa el mismo).
const FONT_FAMILY = "'Geist Variable', system-ui, sans-serif"
// Artboard E: etiqueta de 12,5 px a 8 px de la burbuja. Con un ancho fijo, `truncate` corta con «…»
// los temas largos en lugar de dejarlos cruzar el radar.
const LABEL = { fontSize: 12.5, distance: 8, maxWidthPx: 160 }
// Artboard E: a la derecha de una burbuja con este encaje ya no cabe la etiqueta.
const LABEL_FLIP_FIT_MIN = 76

const STILL_SERIES_ID = 'still'
const PULSE_SERIES_ID = 'pulse'

export function sweepDelaySeconds(fit: number, momentum: number): number {
  const leftward = (SCORE_MAX - fit) * RADAR_ASPECT.width
  const downward = (SCORE_MAX - momentum) * RADAR_ASPECT.height
  const angleDeg = Math.atan2(leftward, downward) * DEGREES_PER_RADIAN
  const progress = (angleDeg + BEAM_DOWN_DEG - SWEEP.fromDeg) / (SWEEP.toDeg - SWEEP.fromDeg)
  return (SWEEP.delayMs + progress * SWEEP.durationMs) / MS_PER_SECOND
}

export type PlottedOpportunity = RankedOpportunity & { audience_fit_score: number }

// Sin encaje no hay posición en X, así que no se dibuja (radarView.ts). `plotted` ya llega así,
// pero el tipo del contrato no lo sabe.
export function isPlotted(opportunity: RankedOpportunity): opportunity is PlottedOpportunity {
  return opportunity.audience_fit_score != null
}

export function detectionDelayMs(opportunity: PlottedOpportunity): number {
  const seconds = sweepDelaySeconds(opportunity.audience_fit_score, opportunity.momentum_score)
  return seconds * MS_PER_SECOND
}

export function bubblePosition(opportunity: PlottedOpportunity, size: PlotSize): PlotPoint {
  return {
    x: (opportunity.audience_fit_score / SCORE_MAX) * size.width,
    y: ((SCORE_MAX - opportunity.momentum_score) / SCORE_MAX) * size.height,
  }
}

interface Focus {
  selectedId: string | null
  hoveredId: string | null
}

export function shownBubbleSize(opportunity: RankedOpportunity, focus: Focus): number {
  const base = bubbleSize(opportunity.evidence_strength)
  if (opportunity.id === focus.selectedId) return base + SELECTED_EXTRA_PX
  if (opportunity.id === focus.hoveredId) return Math.round(base * HOVER_SCALE)
  return base
}

interface Bubble {
  opportunity: PlottedOpportunity
  dimmed: boolean
  pulseSeconds: number | null
}

type PulsingBubble = Bubble & { pulseSeconds: number }

function isPulsing(bubble: Bubble): bubble is PulsingBubble {
  return bubble.pulseSeconds !== null
}

function toBubbles({ plotted, dimmedIds, reducedMotion }: RadarChartInput): Bubble[] {
  return plotted.filter(isPlotted).map((opportunity) => {
    const dimmed = dimmedIds.has(opportunity.id)
    const pulse = pulsePeriodSeconds(opportunity.lifecycle, opportunity.acceleration)
    return { opportunity, dimmed, pulseSeconds: dimmed || reducedMotion ? null : pulse }
  })
}

function bubbleItemStyle({ opportunity, dimmed }: Bubble, palette: LifecyclePalette) {
  const colors = palette[opportunity.lifecycle]
  const opacity = dimmed ? DIMMED_OPACITY : 1
  if (LIFECYCLE_STYLE[opportunity.lifecycle].dashed) {
    return {
      color: WHITE,
      borderColor: colors.stroke,
      borderWidth: HOLLOW_BORDER_PX,
      borderType: 'dashed' as const,
      opacity,
    }
  }
  return { color: colors.fill, borderColor: WHITE, borderWidth: BUBBLE_BORDER_PX, opacity }
}

// La seleccionada no lleva etiqueta: su tema ya está en la tarjeta flotante (artboard E).
function bubbleLabel({ opportunity, dimmed }: Bubble, input: RadarChartInput) {
  const hovered = opportunity.id === input.hoveredId
  return {
    show: input.showLabels && !dimmed && opportunity.id !== input.selectedId,
    formatter: () => opportunity.topic,
    position:
      opportunity.audience_fit_score > LABEL_FLIP_FIT_MIN ? ('left' as const) : ('right' as const),
    distance: LABEL.distance,
    width: LABEL.maxWidthPx,
    overflow: 'truncate' as const,
    ellipsis: '…',
    fontSize: LABEL.fontSize,
    fontWeight: hovered ? 600 : 500,
    color: hovered ? INK : MUTED,
  }
}

function bubbleItem(bubble: Bubble, input: RadarChartInput) {
  return {
    // El id viaja como `name` para que el clic y el hover lo devuelvan tal cual.
    name: bubble.opportunity.id,
    value: [bubble.opportunity.audience_fit_score, bubble.opportunity.momentum_score],
    symbolSize: shownBubbleSize(bubble.opportunity, input),
    itemStyle: bubbleItemStyle(bubble, input.palette),
    label: bubbleLabel(bubble, input),
  }
}

function stillSeries(bubbles: Bubble[], input: RadarChartInput): ScatterSeriesOption {
  const delays = bubbles.map(({ opportunity }) => detectionDelayMs(opportunity))
  return {
    id: STILL_SERIES_ID,
    type: 'scatter',
    clip: false,
    // El hover agranda la burbuja desde `shownBubbleSize`, igual desde el radar que desde el ranking.
    emphasis: { scale: false },
    animationDelay: (index) => delays[index],
    data: bubbles.map((bubble) => bubbleItem(bubble, input)),
  }
}

function pulseSeries(bubbles: PulsingBubble[], input: RadarChartInput): EffectScatterSeriesOption {
  const delays = bubbles.map(({ opportunity }) => detectionDelayMs(opportunity))
  return {
    id: PULSE_SERIES_ID,
    type: 'effectScatter',
    clip: false,
    showEffectOn: 'render',
    rippleEffect: PULSE_RIPPLE,
    emphasis: { scale: false },
    animationDelay: (index) => delays[index],
    data: bubbles.map((bubble) => ({
      ...bubbleItem(bubble, input),
      rippleEffect: {
        period: bubble.pulseSeconds,
        color: input.palette[bubble.opportunity.lifecycle].stroke,
      },
    })),
  }
}

// D9 del plan fe-radar-view: ejes de 0 a 100 ocultos y a sangre, así una burbuja está en
// x = encaje % e y = (100 − momentum) % del área, y las capas HTML se colocan sin convertToPixel.
export function buildRadarOption(input: RadarChartInput): RadarChartOption {
  const bubbles = toBubbles(input)
  const still = bubbles.filter((bubble) => !isPulsing(bubble))
  const pulsing = bubbles.filter(isPulsing)
  const series: (ScatterSeriesOption | EffectScatterSeriesOption)[] = [stillSeries(still, input)]
  if (!input.reducedMotion) series.push(pulseSeries(pulsing, input))
  return {
    animation: !input.reducedMotion,
    animationDuration: ENTRY_DURATION_MS,
    animationEasing: 'backOut',
    animationDurationUpdate: UPDATE_DURATION_MS,
    animationEasingUpdate: 'exponentialOut',
    textStyle: { fontFamily: FONT_FAMILY },
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: { type: 'value', min: 0, max: SCORE_MAX, show: false },
    yAxis: { type: 'value', min: 0, max: SCORE_MAX, show: false },
    series,
  }
}
