import { render } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useRadarQuery } from '../useRadarQuery'

async function mountAt(url: string) {
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: { render: () => null } }],
  })
  let radar!: ReturnType<typeof useRadarQuery>
  const Probe = defineComponent({
    setup() {
      radar = useRadarQuery()
      return () => h('div')
    },
  })
  await router.push(url)
  await router.isReady()
  render(Probe, { global: { plugins: [router] } })
  return { radar, router }
}

describe('useRadarQuery', () => {
  it('uses the default state when the URL has no radar params', async () => {
    const { radar } = await mountAt('/')

    expect(radar.query.value).toEqual({
      period: '7d',
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
  })

  it('reads every radar param from the URL', async () => {
    const { radar } = await mountAt(
      '/?period=24h&lifecycle=emerging&confidence=high&topic=agentes&selected=opp_001&highlight=opp_001,opp_004&gap=1&sort=acceleration&recommendation=publish_now&tab=ranking',
    )

    expect(radar.query.value).toEqual({
      period: '24h',
      lifecycle: ['emerging'],
      confidence: 'high',
      topic: 'agentes',
      selected: 'opp_001',
      highlight: ['opp_001', 'opp_004'],
      gap: true,
      sort: 'acceleration',
      recommendation: 'publish_now',
      tab: 'ranking',
    })
  })

  it('ignores values outside the contract enums', async () => {
    const { radar } = await mountAt(
      '/?period=1y&lifecycle=viral&confidence=total&recommendation=go_viral',
    )

    expect(radar.query.value.period).toBe('7d')
    expect(radar.query.value.lifecycle).toEqual([])
    expect(radar.query.value.confidence).toBeNull()
    expect(radar.query.value.recommendation).toBeNull()
  })

  it('takes the first value when a param is repeated', async () => {
    const { radar } = await mountAt('/?lifecycle=peaking&lifecycle=emerging')

    expect(radar.query.value.lifecycle).toEqual(['peaking'])
  })

  it('keeps the valid stages of a list once, in their order', async () => {
    const { radar } = await mountAt('/?lifecycle=emerging,bogus,peaking,emerging')

    expect(radar.query.value.lifecycle).toEqual(['emerging', 'peaking'])
  })

  it('reads the LATAM gap and the ranking sort and writes them back unchanged', async () => {
    const { radar, router } = await mountAt('/?gap=1&sort=acceleration')

    expect(radar.query.value.gap).toBe(true)
    expect(radar.query.value.sort).toBe('acceleration')

    await radar.update({})

    expect(router.currentRoute.value.query).toEqual({ gap: '1', sort: 'acceleration' })
  })

  it('reads the recommendation filter and writes it back unchanged', async () => {
    const { radar, router } = await mountAt('/?recommendation=publish_now')

    expect(radar.query.value.recommendation).toBe('publish_now')

    await radar.update({})

    expect(router.currentRoute.value.query).toEqual({ recommendation: 'publish_now' })
  })

  it('writes a patch to the URL and keeps unrelated params', async () => {
    const { radar, router } = await mountAt('/?lifecycle=peaking&utm=demo')

    await radar.update({ period: '30d', highlight: ['opp_002', 'opp_003'] })

    expect(router.currentRoute.value.query).toEqual({
      period: '30d',
      lifecycle: 'peaking',
      highlight: 'opp_002,opp_003',
      utm: 'demo',
    })
  })

  it('drops params that go back to their default', async () => {
    const { radar, router } = await mountAt('/?period=24h&lifecycle=peaking&highlight=opp_001')

    await radar.update({ period: '7d', lifecycle: [], highlight: [] })

    expect(router.currentRoute.value.query).toEqual({})
  })

  it('drops the stage, gap, recommendation and sort params on reset and keeps unrelated params', async () => {
    const { radar, router } = await mountAt(
      '/?lifecycle=peaking,saturated&gap=1&recommendation=publish_now&sort=acceleration&utm=demo',
    )

    await radar.update({ lifecycle: [], gap: false, recommendation: null, sort: 'opportunity' })

    expect(router.currentRoute.value.query).toEqual({ utm: 'demo' })
  })
})
