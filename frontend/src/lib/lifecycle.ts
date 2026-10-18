import type { components } from '@/types/api'

import type { Lifecycle } from './radarQuery'

interface LifecycleCssVars {
  fill: string
  stroke: string
  bg: string
  fg: string
}

export interface LifecycleStyle {
  label: string
  // La regla de CLAUDE.md §7 en palabras de quien decide qué publicar; `lifecycle_reason` (la
  // regla con sus cifras) queda en el tooltip.
  meaning: string
  cssVar: LifecycleCssVars
  // "Sin tendencia clara" se dibuja hueca, con trazo discontinuo (DESIGN.md §2).
  dashed: boolean
}

export interface LifecycleColors {
  fill: string
  stroke: string
}

export type LifecyclePalette = Record<Lifecycle, LifecycleColors>

// Acelerando y En pico tienen un trazo propio, más oscuro que el relleno (DESIGN.md §2); el resto
// traza con su relleno.
type StrokeVar = `--lc-${Lifecycle}` | '--lc-accelerating-stroke' | '--lc-peaking-stroke'

function cssVars(name: Lifecycle, stroke: StrokeVar): LifecycleCssVars {
  return {
    fill: `--lc-${name}`,
    stroke,
    bg: `--lc-${name}-bg`,
    fg: `--lc-${name}-fg`,
  }
}

// Un solo mapa para el radar, los chips y la leyenda (DESIGN.md §11). El `Record` obliga a
// cubrir todas las etapas del contrato.
export const LIFECYCLE_STYLE: Record<Lifecycle, LifecycleStyle> = {
  emerging: {
    label: 'Emergente',
    meaning: 'empieza a crecer, en pocas fuentes y con poco contenido parecido.',
    cssVar: cssVars('emerging', '--lc-emerging'),
    dashed: false,
  },
  accelerating: {
    label: 'Acelerando',
    meaning: 'crece más de un 50 % y aparece en 3 fuentes o más.',
    cssVar: cssVars('accelerating', '--lc-accelerating-stroke'),
    dashed: false,
  },
  peaking: {
    label: 'En pico',
    meaning: 'ya hay mucho contenido parecido y casi no crece.',
    cssVar: cssVars('peaking', '--lc-peaking-stroke'),
    dashed: false,
  },
  saturated: {
    label: 'Saturado',
    meaning: 'hay mucho contenido parecido y empieza a bajar.',
    cssVar: cssVars('saturated', '--lc-saturated'),
    dashed: false,
  },
  unknown: {
    label: 'Sin tendencia clara',
    meaning: 'faltan datos o ninguna regla de etapa se cumple.',
    cssVar: cssVars('unknown', '--lc-unknown'),
    dashed: true,
  },
}

// El contrato no tiene etapa `declining`: el backend deja el tema sin etapa y escribe
// «En descenso:» en `lifecycle_reason` justo cuando hay datos y la aceleración es negativa
// (`intelligence/lifecycle.py`). Se nombra aquí; el color sigue siendo el de sin etapa.
export const DESCENDING_STYLE: LifecycleStyle = {
  ...LIFECYCLE_STYLE.unknown,
  label: 'En descenso',
  meaning: 'tiene datos, pero publica menos que en la ventana anterior y ninguna etapa aplica.',
}

type StageSignals = Pick<
  components['schemas']['Opportunity'],
  'lifecycle' | 'growth_status' | 'acceleration'
>

export function isDescending(topic: StageSignals): boolean {
  return (
    topic.lifecycle === 'unknown' && topic.growth_status !== 'preliminary' && topic.acceleration < 0
  )
}

export function topicStageStyle(topic: StageSignals): LifecycleStyle {
  return isDescending(topic) ? DESCENDING_STYLE : LIFECYCLE_STYLE[topic.lifecycle]
}

// ECharts pinta en canvas y necesita colores resueltos, no `var(--…)`.
export function resolveLifecyclePalette(style: CSSStyleDeclaration): LifecyclePalette {
  const read = (name: string) => style.getPropertyValue(name).trim()
  const entries = Object.entries(LIFECYCLE_STYLE).map(([lifecycle, { cssVar }]) => [
    lifecycle,
    { fill: read(cssVar.fill), stroke: read(cssVar.stroke) },
  ])
  return Object.fromEntries(entries) as LifecyclePalette
}
