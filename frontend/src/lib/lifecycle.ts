import type { Lifecycle } from './radarQuery'

interface LifecycleCssVars {
  fill: string
  stroke: string
  bg: string
  fg: string
}

export interface LifecycleStyle {
  label: string
  cssVar: LifecycleCssVars
  // "Sin etapa" se dibuja hueca, con trazo discontinuo (DESIGN.md §2).
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
  emerging: { label: 'Emergente', cssVar: cssVars('emerging', '--lc-emerging'), dashed: false },
  accelerating: {
    label: 'Acelerando',
    cssVar: cssVars('accelerating', '--lc-accelerating-stroke'),
    dashed: false,
  },
  peaking: { label: 'En pico', cssVar: cssVars('peaking', '--lc-peaking-stroke'), dashed: false },
  saturated: { label: 'Saturado', cssVar: cssVars('saturated', '--lc-saturated'), dashed: false },
  unknown: { label: 'Sin etapa', cssVar: cssVars('unknown', '--lc-unknown'), dashed: true },
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
