import { computed } from 'vue'
import { useRoute, useRouter, type LocationQuery } from 'vue-router'

import {
  parseRadarQuery,
  RADAR_QUERY_KEYS,
  serializeRadarQuery,
  type RadarQuery,
} from '@/lib/radarQuery'

// Enlaces compartidos cuando el Radar tenía filtro de periodo: se ignoran y se limpian al cambiar.
const RETIRED_KEYS = ['period'] as const

export function useRadarQuery() {
  const route = useRoute()
  const router = useRouter()

  const query = computed(() => parseRadarQuery(route.query))

  // `replace` y no `push`: cambiar un filtro no debe llenar el historial del navegador.
  async function update(patch: Partial<RadarQuery>) {
    const unrelated: LocationQuery = { ...route.query }
    for (const key of [...RADAR_QUERY_KEYS, ...RETIRED_KEYS]) delete unrelated[key]
    await router.replace({
      query: { ...unrelated, ...serializeRadarQuery({ ...query.value, ...patch }) },
    })
  }

  return { query, update }
}
