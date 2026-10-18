import type { components } from '@/types/api'

import { countLabel, formatRatio } from './evidenceFormat'

type OutlierHooks = components['schemas']['OutlierHooks']
type HookLift = components['schemas']['HookLift']

// Las opciones de gancho de la batería de pieza de Jev (`piece.v3.yaml`, pregunta `hook`).
const HOOK_LABEL: Record<string, string> = {
  question: 'Pregunta',
  data: 'Dato o cifra',
  counterintuitive: 'Algo contraintuitivo',
  story: 'Historia',
  how_to: 'Cómo hacer algo',
  news: 'Noticia',
  list: 'Lista',
}

export interface HookRow {
  hook: string
  label: string
  outliers: string
  rest: string
  comparison: string
  verdict: string
  observed: boolean
}

// `lift` es null cuando ninguna pieza del resto usa el gancho: no es 0 ni infinito, se dice.
function comparison(hook: HookLift): string {
  if (hook.rest_total === 0) return 'sin piezas del resto con las que comparar'
  if (hook.lift === null) return 'ninguna pieza del resto lo usa'
  if (hook.lift > 1) return `${formatRatio(hook.lift)} más que en el resto`
  if (hook.lift === 1) return 'igual que en el resto'
  return 'menos que en el resto'
}

function toRow(hook: HookLift): HookRow {
  return {
    hook: hook.hook,
    label: HOOK_LABEL[hook.hook] ?? hook.hook,
    outliers: `${hook.outliers_with} de ${countLabel(hook.outliers_total, 'outlier', 'outliers')}`,
    rest: hook.rest_total === 0 ? 'sin resto' : `${hook.rest_with} de ${hook.rest_total} del resto`,
    comparison: comparison(hook),
    // CLAUDE.md §7: lift ≥ 2 en ≥ 2 outliers es «patrón observado»; lo demás, anecdótico.
    verdict: hook.observed_pattern ? 'Patrón observado' : 'Anecdótico',
    observed: hook.observed_pattern,
  }
}

export function hookRows(hooks: OutlierHooks): HookRow[] {
  return [...hooks.hooks]
    .sort(
      (a, b) =>
        Number(b.observed_pattern) - Number(a.observed_pattern) ||
        b.outliers_with - a.outliers_with,
    )
    .map(toRow)
}

export function unclassifiedNote(hooks: OutlierHooks): string | null {
  if (hooks.outliers_unclassified === 0) return null
  return `${countLabel(hooks.outliers_unclassified, 'outlier', 'outliers')} sin gancho clasificado.`
}
