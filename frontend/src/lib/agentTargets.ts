import type { RouteLocationRaw, RouteRecordNameGeneric } from 'vue-router'

import { RouteName } from '@/router/routeNames'

import type { AgentScreen, AgentTarget, DossierSection, Navigation, RadarPatch } from './agentTypes'
import { EXPLORE_TEXT_PARAM } from './exploreView'
import { DEFAULT_RANKING_SORT, type RadarQuery } from './radarQuery'
import { activeCounterOf, type CounterFilter } from './radarView'

// D8 del plan fe-radar-agent: a dónde va la presencia de Rad antes de actuar. Cada objetivo es el
// valor de `data-agent` de un elemento de la página.

// La presencia de Rad es una capa absoluta sobre esta raíz (DESIGN.md §7): sus coordenadas, y
// las de la mirada de su marca, son relativas a ella.
export const AGENT_ROOT_SELECTOR = '[data-agent-root]'

export const AGENT_ANCHOR = {
  radar: 'radar',
  ranking: 'ranking',
  detail: 'detail',
  reset: 'reset',
  composer: 'composer',
  pieces: 'pieces',
  navRadar: 'nav-radar',
  navExplore: 'nav-explore',
  openDossier: 'open-dossier',
} as const

// Las burbujas son canvas: su ancla es un elemento invisible en la posición de la burbuja.
export const bubbleAnchor = (id: string) => `bubble-${id}`
export const rowAnchor = (id: string) => `row-${id}`

export const SECTION_ANCHOR: Record<DossierSection, string> = {
  score: 'dossier-score',
  evolution: 'dossier-evolution',
  fit: 'dossier-fit',
  evidence: 'dossier-evidence',
  // «Qué no sabemos» salió de la UI (18/10): la sección lleva a «Por qué importa».
  limits: 'dossier-why',
}

const DEFAULT_SECTION: DossierSection = 'score'

// Los mismos valores que los contadores de RadarHero.vue.
export const COUNTER_ANCHOR: Record<CounterFilter, string> = {
  publish_now: 'filter-rec-publish_now',
  accelerating: 'filter-lc-accelerating',
  emerging: 'filter-lc-emerging',
  unknown: 'filter-lc-unknown',
}

const control = (anchor: string): AgentTarget => ({ anchor, kind: 'control' })
const block = (anchor: string): AgentTarget => ({ anchor, kind: 'block' })
const point = (anchor: string): AgentTarget => ({ anchor, kind: 'point' })

const MAIN_BLOCK: Record<AgentScreen, string> = {
  radar: AGENT_ANCHOR.radar,
  dossier: SECTION_ANCHOR.score,
  explore: AGENT_ANCHOR.pieces,
}

// Solo cambian las claves presentes; un `null` quita ese filtro (contrato de `RadarPatch`).
export function patchToQuery(patch: RadarPatch): Partial<RadarQuery> {
  const query: Partial<RadarQuery> = {}
  if (patch.lifecycle !== undefined) query.lifecycle = patch.lifecycle ?? []
  if (patch.recommendation !== undefined) query.recommendation = patch.recommendation
  if (patch.confidence !== undefined) query.confidence = patch.confidence
  if (patch.topic !== undefined) query.topic = patch.topic
  if (patch.gap !== undefined) query.gap = patch.gap ?? false
  if (patch.sort !== undefined) query.sort = patch.sort ?? DEFAULT_RANKING_SORT
  // Un orden solo se ve en el ranking: Rad lo enseña en su pestaña.
  if (patch.sort) query.tab = 'ranking'
  if (patch.selected !== undefined) query.selected = patch.selected
  if (patch.highlight !== undefined) query.highlight = patch.highlight ?? []
  return query
}

interface PatchContext {
  // Estado del Radar antes de aplicar el parche.
  query: RadarQuery
  hasAnchor: (anchor: string) => boolean
}

function selectionTarget(id: string, hasAnchor: PatchContext['hasAnchor']): AgentTarget {
  if (hasAnchor(bubbleAnchor(id))) return point(bubbleAnchor(id))
  // Un tema sin encaje no tiene burbuja, y sin la pestaña Ranking (o con el ranking plegado) no
  // hay fila: su vista previa sale en el panel de al lado.
  if (hasAnchor(rowAnchor(id))) return control(rowAnchor(id))
  return block(AGENT_ANCHOR.detail)
}

function counterTarget(patch: RadarPatch, { query, hasAnchor }: PatchContext): AgentTarget | null {
  if (patch.lifecycle === undefined && patch.recommendation === undefined) return null
  const counter = activeCounterOf({ ...query, ...patchToQuery(patch) })
  // «Sin tendencia clara» filtra por URL pero no tiene contador en la cabecera.
  if (counter === null || !hasAnchor(COUNTER_ANCHOR[counter])) return null
  return control(COUNTER_ANCHOR[counter])
}

// Lo mismo que quitan `resetViewPatch()` y el `reset_view` del agente.
function isReset(patch: RadarPatch): boolean {
  return patch.lifecycle?.length === 0 && patch.gap === false && patch.highlight?.length === 0
}

function isSortOnly(patch: RadarPatch): boolean {
  const keys = Object.keys(patch)
  return keys.length === 1 && patch.sort !== undefined
}

export function patchTarget(patch: RadarPatch, { query, hasAnchor }: PatchContext): AgentTarget {
  if (patch.selected) return selectionTarget(patch.selected, hasAnchor)
  const counter = counterTarget(patch, { query, hasAnchor })
  if (counter !== null) return counter
  if (isReset(patch)) {
    return hasAnchor(AGENT_ANCHOR.reset) ? control(AGENT_ANCHOR.reset) : block(AGENT_ANCHOR.radar)
  }
  if (isSortOnly(patch)) return block(AGENT_ANCHOR.ranking)
  return block(AGENT_ANCHOR.radar)
}

// Los pasos de datos señalan el bloque principal de la pantalla.
export function dataStepTarget(screen: AgentScreen): AgentTarget {
  return block(MAIN_BLOCK[screen])
}

interface NavigationContext {
  screen: AgentScreen | null
  // Tema seleccionado en el Radar o abierto en el expediente.
  opportunityId: string | null
  previewOpen: boolean
}

function dossierEntry(nav: Navigation, from: NavigationContext): AgentTarget | null {
  const isSameTopic = from.opportunityId === nav.opportunity_id
  if (from.screen === 'dossier' && isSameTopic) return null
  if (from.screen === 'radar' && from.previewOpen && isSameTopic) {
    return control(AGENT_ANCHOR.openDossier)
  }
  return control(AGENT_ANCHOR.navExplore)
}

function screenEntry(screen: AgentScreen, from: NavigationContext): AgentTarget | null {
  if (from.screen === screen) return null
  return control(screen === 'radar' ? AGENT_ANCHOR.navRadar : AGENT_ANCHOR.navExplore)
}

// `before`: el control que lleva allí (lo pulsa la presencia); `after`: lo que enseña al llegar.
export function navigationTargets(
  nav: Navigation,
  from: NavigationContext,
): { before: AgentTarget | null; after: AgentTarget } {
  if (nav.screen === 'dossier') {
    const section = nav.section ?? DEFAULT_SECTION
    return { before: dossierEntry(nav, from), after: block(SECTION_ANCHOR[section]) }
  }
  return { before: screenEntry(nav.screen, from), after: dataStepTarget(nav.screen) }
}

// Un expediente sin id no tiene ruta: se abre Explorar, que lista todos los temas.
export function navigationRoute(nav: Navigation): RouteLocationRaw {
  if (nav.screen === 'dossier' && nav.opportunity_id) {
    return { name: RouteName.Dossier, params: { id: nav.opportunity_id } }
  }
  if (nav.screen === 'radar') return { name: RouteName.Discover }
  const query = nav.search ? { [EXPLORE_TEXT_PARAM]: nav.search } : {}
  return { name: RouteName.Explore, query }
}

export function screenOf(routeName: RouteRecordNameGeneric | null | undefined): AgentScreen | null {
  if (routeName === RouteName.Discover) return 'radar'
  if (routeName === RouteName.Explore) return 'explore'
  if (routeName === RouteName.Dossier) return 'dossier'
  return null
}
