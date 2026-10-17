import type { EffectScatterSeriesOption, ScatterSeriesOption } from 'echarts/charts'
import type { GridComponentOption } from 'echarts/components'
import type { ComposeOption } from 'echarts/core'

import { LIFECYCLE_STYLE, type LifecyclePalette } from './lifecycle'
import { bubbleSize, pulsePeriodSeconds, SCORE_MAX } from './opportunityFormat'
import type { PlottedOpportunity, RankedOpportunity } from './radarView'

export type RadarChartOption = ComposeOption<
  ScatterSeriesOption | EffectScatterSeriesOption | GridComponentOption
>

export interface RadarChartInput {
  plotted: PlottedOpportunity[]
  dimmedIds: Set<string>
  selectedId: string | null
  hoveredId: string | null
  palette: LifecyclePalette
  reducedMotion: boolean
  showLabels: boolean
  // `true` mientras el haz barre: sin anillos ni etiquetas (D13).
  entering: boolean
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
const TRANSPARENT = 'transparent'
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

const BUBBLE_SERIES_ID = 'bubbles'
const RING_SERIES_ID = 'rings'

export function sweepDelaySeconds(fit: number, momentum: number): number {
  const leftward = (SCORE_MAX - fit) * RADAR_ASPECT.width
  const downward = (SCORE_MAX - momentum) * RADAR_ASPECT.height
  const angleDeg = Math.atan2(leftward, downward) * DEGREES_PER_RADIAN
  const progress = (angleDeg + BEAM_DOWN_DEG - SWEEP.fromDeg) / (SWEEP.toDeg - SWEEP.fromDeg)
  return (SWEEP.delayMs + progress * SWEEP.durationMs) / MS_PER_SECOND
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

export const translateTo = ({ x, y }: PlotPoint) => `translate(${x}px, ${y}px)`

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
}

interface Ring {
  opportunity: PlottedOpportunity
  periodSeconds: number
}

function toBubbles({ plotted, dimmedIds }: RadarChartInput): Bubble[] {
  return plotted.map((opportunity) => ({ opportunity, dimmed: dimmedIds.has(opportunity.id) }))
}

// DESIGN.md §8: lo atenuado pierde el latido.
function toRings(bubbles: Bubble[]): Ring[] {
  return bubbles.flatMap(({ opportunity, dimmed }) => {
    const periodSeconds = pulsePeriodSeconds(opportunity.lifecycle, opportunity.acceleration)
    return dimmed || periodSeconds === null ? [] : [{ opportunity, periodSeconds }]
  })
}

function plotValue(opportunity: PlottedOpportunity): [number, number] {
  return [opportunity.audience_fit_score, opportunity.momentum_score]
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
function isLabelShown({ opportunity, dimmed }: Bubble, input: RadarChartInput): boolean {
  if (!input.showLabels || input.entering || dimmed) return false
  return opportunity.id !== input.selectedId
}

function bubbleLabel(bubble: Bubble, input: RadarChartInput) {
  const { opportunity } = bubble
  const hovered = opportunity.id === input.hoveredId
  return {
    show: isLabelShown(bubble, input),
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
    value: plotValue(bubble.opportunity),
    symbolSize: shownBubbleSize(bubble.opportunity, input),
    itemStyle: bubbleItemStyle(bubble, input.palette),
    label: bubbleLabel(bubble, input),
  }
}

// Todas las burbujas en una sola serie, también las que laten: así entran con el retardo del
// barrido y, al atenuarse, cambian de opacidad en su sitio en lugar de pasar a otra serie y
// volver a entrar (D13).
function bubbleSeries(bubbles: Bubble[], input: RadarChartInput): ScatterSeriesOption {
  const delays = bubbles.map(({ opportunity }) => detectionDelayMs(opportunity))
  return {
    id: BUBBLE_SERIES_ID,
    type: 'scatter',
    clip: false,
    // El hover agranda la burbuja desde `shownBubbleSize`, igual desde el radar que desde el ranking.
    emphasis: { scale: false },
    // Entre dos etiquetas que chocan, ECharts deja la de la burbuja más grande (su prioridad es el
    // área), que es la de más evidencia. Solo compara etiquetas entre sí, no con burbujas.
    labelLayout: { hideOverlap: true },
    // El retardo es solo para la entrada: `LabelLayout` lo reutiliza al fundir cada etiqueta nueva,
    // y tras el barrido las retrasaría hasta 1,3 s más.
    animationDelay: input.entering ? (index) => delays[index] : 0,
    data: bubbles.map((bubble) => bubbleItem(bubble, input)),
  }
}

// El `EffectSymbol` de ECharts rehace su entrada sin `animationDelay`: solo pinta el anillo, sobre
// un símbolo transparente del tamaño de la burbuja, y `silent` deja el clic y el hover a la burbuja.
function ringSeries(rings: Ring[], input: RadarChartInput): EffectScatterSeriesOption {
  return {
    id: RING_SERIES_ID,
    type: 'effectScatter',
    silent: true,
    clip: false,
    showEffectOn: 'render',
    rippleEffect: PULSE_RIPPLE,
    data: rings.map(({ opportunity, periodSeconds }) => ({
      name: opportunity.id,
      value: plotValue(opportunity),
      symbolSize: shownBubbleSize(opportunity, input),
      itemStyle: { color: TRANSPARENT },
      rippleEffect: { period: periodSeconds, color: input.palette[opportunity.lifecycle].stroke },
    })),
  }
}

// D9 del plan fe-radar-view: ejes de 0 a 100 ocultos y a sangre, así una burbuja está en
// x = encaje % e y = (100 − momentum) % del área, y las capas HTML se colocan sin convertToPixel.
export function buildRadarOption(input: RadarChartInput): RadarChartOption {
  const bubbles = toBubbles(input)
  // Durante el barrido aún no late nada: cada anillo saldría antes que su burbuja (D13).
  const rings = input.entering ? [] : toRings(bubbles)
  const series: (ScatterSeriesOption | EffectScatterSeriesOption)[] = [bubbleSeries(bubbles, input)]
  if (!input.reducedMotion) series.push(ringSeries(rings, input))
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
