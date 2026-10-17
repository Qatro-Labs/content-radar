<script setup lang="ts">
import { computed } from 'vue'

import { useOpportunities } from '@/api/opportunities'
import { useRadarQuery } from '@/composables/useRadarQuery'
import { PERIODS, type Period } from '@/lib/radarQuery'

const PERIOD_LABEL: Record<Period, string> = {
  '24h': '24 h',
  '7d': '7 días',
  '30d': '30 días',
}

const { query, update } = useRadarQuery()
// Misma `queryKey` que la vista: TanStack Query comparte la caché y no repite la petición.
const { data } = useOpportunities(() => query.value.period)

// La API solo calcula algunos periodos y responde con el real: si difiere del pedido, se dice
// en lugar de dejar que se lea como el periodo elegido (CLAUDE.md §2.3).
const periodServedInstead = computed(() => {
  const served = data.value?.period
  return served && served !== query.value.period ? served : null
})
</script>

<template>
  <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
    <div role="group" aria-label="Periodo" class="flex gap-0.5 rounded-lg bg-input p-1">
      <button
        v-for="period in PERIODS"
        :key="period"
        type="button"
        :aria-pressed="query.period === period"
        class="flex min-h-9 items-center rounded-[9px] px-3.5 text-sm font-medium text-ink-soft transition duration-150 ease-out hover:text-foreground active:scale-[0.98] aria-pressed:bg-card aria-pressed:font-semibold aria-pressed:text-foreground"
        @click="update({ period })"
      >
        {{ PERIOD_LABEL[period] }}
      </button>
    </div>

    <p
      v-if="periodServedInstead"
      class="text-[13px] font-medium text-notice-foreground"
      role="status"
    >
      Solo hay datos calculados para {{ PERIOD_LABEL[periodServedInstead] }}
    </p>
  </div>
</template>
