import { describe, expect, it } from 'vitest'

import { dataStepTarget, navigationTargets, patchTarget, patchToQuery } from '../agentTargets'
import type { AgentScreen, AgentTarget, Navigation, RadarPatch } from '../agentTypes'
import { parseRadarQuery, type RadarQuery } from '../radarQuery'

const DEFAULT_QUERY = parseRadarQuery({})

describe('patchToQuery', () => {
  it('turns a null into the empty value of each filter', () => {
    expect(patchToQuery({ lifecycle: null, gap: null, sort: null, confidence: null })).toEqual({
      lifecycle: [],
      gap: false,
      sort: 'opportunity',
      confidence: null,
    })
  })

  it('opens the ranking tab to show a sort', () => {
    expect(patchToQuery({ sort: 'acceleration' })).toEqual({ sort: 'acceleration', tab: 'ranking' })
  })

  it('leaves out the keys the patch does not bring', () => {
    expect(patchToQuery({ highlight: ['opp_001'], selected: 'opp_001' })).toStrictEqual({
      highlight: ['opp_001'],
      selected: 'opp_001',
    })
  })
})

describe('patchTarget', () => {
  const RESET: RadarPatch = {
    lifecycle: [],
    gap: false,
    highlight: [],
    recommendation: null,
    confidence: null,
    topic: null,
  }

  it.each<{
    case: string
    patch: RadarPatch
    anchors: string[]
    query?: RadarQuery
    target: AgentTarget
  }>([
    {
      case: 'a selection goes to its bubble',
      patch: { selected: 'opp_001' },
      anchors: ['bubble-opp_001', 'row-opp_001'],
      target: { anchor: 'bubble-opp_001', kind: 'point' },
    },
    {
      case: 'a selection without a bubble goes to its ranking row',
      patch: { selected: 'opp_001' },
      anchors: ['row-opp_001'],
      target: { anchor: 'row-opp_001', kind: 'control' },
    },
    {
      case: 'a selection without a bubble or a row goes to its preview beside',
      patch: { selected: 'opp_011' },
      anchors: [],
      target: { anchor: 'detail', kind: 'block' },
    },
    {
      case: 'a filter equal to a counter presses that counter',
      patch: { lifecycle: ['accelerating'] },
      anchors: ['reset', 'filter-lc-accelerating'],
      target: { anchor: 'filter-lc-accelerating', kind: 'control' },
    },
    {
      case: 'publish now presses its counter',
      patch: { recommendation: 'publish_now' },
      anchors: ['filter-rec-publish_now'],
      target: { anchor: 'filter-rec-publish_now', kind: 'control' },
    },
    {
      case: 'a stage without a counter presses its chip in the legend',
      patch: { lifecycle: ['peaking'] },
      anchors: ['reset', 'legend-lc-peaking'],
      target: { anchor: 'legend-lc-peaking', kind: 'control' },
    },
    {
      case: 'a stage with a counter presses the counter, not the legend',
      patch: { lifecycle: ['emerging'] },
      anchors: ['filter-lc-emerging', 'legend-lc-emerging'],
      target: { anchor: 'filter-lc-emerging', kind: 'control' },
    },
    {
      case: 'a counter that is not on screen leaves the presence on the radar',
      patch: { lifecycle: ['unknown'] },
      anchors: [],
      target: { anchor: 'radar', kind: 'block' },
    },
    {
      case: 'a reset presses «Restablecer vista»',
      patch: RESET,
      anchors: ['reset'],
      query: { ...DEFAULT_QUERY, lifecycle: ['peaking'] },
      target: { anchor: 'reset', kind: 'control' },
    },
    {
      case: 'a reset without the button goes to the radar',
      patch: RESET,
      anchors: [],
      target: { anchor: 'radar', kind: 'block' },
    },
    {
      case: 'a sort alone goes to the ranking',
      patch: { sort: 'acceleration' },
      anchors: [],
      target: { anchor: 'ranking', kind: 'block' },
    },
    {
      case: 'a highlight goes to the radar',
      patch: { highlight: ['opp_001', 'opp_002'] },
      anchors: ['bubble-opp_001'],
      target: { anchor: 'radar', kind: 'block' },
    },
  ])('$case', ({ patch, anchors, query = DEFAULT_QUERY, target }) => {
    const hasAnchor = (anchor: string) => anchors.includes(anchor)

    expect(patchTarget(patch, { query, hasAnchor })).toEqual(target)
  })
})

describe('navigationTargets', () => {
  it.each<{
    case: string
    nav: Navigation
    from: { screen: AgentScreen | null; opportunityId: string | null; previewOpen: boolean }
    before: AgentTarget | null
    after: AgentTarget
  }>([
    {
      case: 'dossier already open: straight to the section',
      nav: { screen: 'dossier', opportunity_id: 'opp_001', section: 'evidence' },
      from: { screen: 'dossier', opportunityId: 'opp_001', previewOpen: false },
      before: null,
      after: { anchor: 'dossier-evidence', kind: 'block' },
    },
    {
      case: 'dossier from the radar preview of that topic: «Ver expediente →»',
      nav: { screen: 'dossier', opportunity_id: 'opp_001', section: 'limits' },
      from: { screen: 'radar', opportunityId: 'opp_001', previewOpen: true },
      before: { anchor: 'open-dossier', kind: 'control' },
      after: { anchor: 'dossier-why', kind: 'block' },
    },
    {
      case: 'dossier from anywhere else: «Explorar» in the nav, score by default',
      nav: { screen: 'dossier', opportunity_id: 'opp_002' },
      from: { screen: 'radar', opportunityId: 'opp_001', previewOpen: true },
      before: { anchor: 'nav-explore', kind: 'control' },
      after: { anchor: 'dossier-score', kind: 'block' },
    },
    {
      case: 'explore already open',
      nav: { screen: 'explore', search: 'agentes' },
      from: { screen: 'explore', opportunityId: null, previewOpen: false },
      before: null,
      after: { anchor: 'pieces', kind: 'block' },
    },
    {
      case: 'explore from a dossier',
      nav: { screen: 'explore', search: 'agentes' },
      from: { screen: 'dossier', opportunityId: 'opp_001', previewOpen: false },
      before: { anchor: 'nav-explore', kind: 'control' },
      after: { anchor: 'pieces', kind: 'block' },
    },
    {
      case: 'radar already open',
      nav: { screen: 'radar' },
      from: { screen: 'radar', opportunityId: null, previewOpen: false },
      before: null,
      after: { anchor: 'radar', kind: 'block' },
    },
    {
      case: 'radar from explore',
      nav: { screen: 'radar' },
      from: { screen: 'explore', opportunityId: null, previewOpen: false },
      before: { anchor: 'nav-radar', kind: 'control' },
      after: { anchor: 'radar', kind: 'block' },
    },
  ])('$case', ({ nav, from, before, after }) => {
    expect(navigationTargets(nav, from)).toEqual({ before, after })
  })
})

describe('dataStepTarget', () => {
  it.each<{ screen: AgentScreen; anchor: string }>([
    { screen: 'radar', anchor: 'radar' },
    { screen: 'dossier', anchor: 'dossier-score' },
    { screen: 'explore', anchor: 'pieces' },
  ])('points at the main block of $screen', ({ screen, anchor }) => {
    expect(dataStepTarget(screen)).toEqual({ anchor, kind: 'block' })
  })
})
