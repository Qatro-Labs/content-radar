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

function cssVars(name: string, { ownStroke }: { ownStroke: boolean }): LifecycleCssVars {
  return {
    fill: `--lc-${name}`,
    stroke: ownStroke ? `--lc-${name}-stroke` : `--lc-${name}`,
    bg: `--lc-${name}-bg`,
    fg: `--lc-${name}-fg`,
  }
}

// Un solo mapa para el radar, los chips y la leyenda (DESIGN.md §11). El `Record` obliga a
// cubrir todas las etapas del contrato.
export const LIFECYCLE_STYLE: Record<Lifecycle, LifecycleStyle> = {
  emerging: {
    label: 'Emergente',
    cssVar: cssVars('emerging', { ownStroke: false }),
    dashed: false,
  },
  accelerating: {
    label: 'Acelerando',
    cssVar: cssVars('accelerating', { ownStroke: true }),
    dashed: false,
  },
  peaking: { label: 'En pico', cssVar: cssVars('peaking', { ownStroke: true }), dashed: false },
  saturated: {
    label: 'Saturado',
    cssVar: cssVars('saturated', { ownStroke: false }),
    dashed: false,
  },
  unknown: { label: 'Sin etapa', cssVar: cssVars('unknown', { ownStroke: false }), dashed: true },
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
