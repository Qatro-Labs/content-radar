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
      lifecycle: null,
      confidence: null,
      topic: null,
      selected: null,
      highlight: [],
    })
  })

  it('reads every radar param from the URL', async () => {
    const { radar } = await mountAt(
      '/?period=24h&lifecycle=emerging&confidence=high&topic=agentes&selected=opp_001&highlight=opp_001,opp_004',
    )

    expect(radar.query.value).toEqual({
      period: '24h',
      lifecycle: 'emerging',
      confidence: 'high',
      topic: 'agentes',
      selected: 'opp_001',
      highlight: ['opp_001', 'opp_004'],
    })
  })

  it('ignores values outside the contract enums', async () => {
    const { radar } = await mountAt('/?period=1y&lifecycle=viral&confidence=total')

    expect(radar.query.value.period).toBe('7d')
    expect(radar.query.value.lifecycle).toBeNull()
    expect(radar.query.value.confidence).toBeNull()
  })

  it('takes the first value when a param is repeated', async () => {
    const { radar } = await mountAt('/?lifecycle=peaking&lifecycle=emerging')

    expect(radar.query.value.lifecycle).toBe('peaking')
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

    await radar.update({ period: '7d', lifecycle: null, highlight: [] })

    expect(router.currentRoute.value.query).toEqual({})
  })
})
