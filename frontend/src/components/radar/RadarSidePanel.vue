<script setup lang="ts">
import type { RadarView } from '@/lib/radarView'

import OpportunityPreview from './OpportunityPreview.vue'
import WeekSummary from './WeekSummary.vue'

const { view, monitoringStartedAt } = defineProps<{
  view: RadarView
  monitoringStartedAt: string
}>()

const emit = defineEmits<{
  select: [id: string]
  hover: [id: string | null]
  clear: []
}>()
</script>

<template>
  <!-- Debajo del radar y del ranking, a lo ancho: «Esta semana» o la vista previa del tema. -->
  <aside aria-label="Panel del tema" class="flex min-w-0 flex-col rounded-card bg-card p-[22px]">
    <!-- DESIGN.md §7: cambia de estado con fundido y 6 px de subida (280 ms). La vista previa no
         se remonta al cambiar de tema: así el anillo cuenta hasta el nuevo valor. -->
    <Transition
      mode="out-in"
      enter-from-class="translate-y-1.5 opacity-0"
      enter-active-class="transition duration-[280ms] ease-out motion-reduce:transition-none"
    >
      <OpportunityPreview
        v-if="view.selected"
        :opportunity="view.selected"
        :total="view.total"
        @clear="emit('clear')"
      />
      <WeekSummary
        v-else
        :view
        :monitoring-started-at="monitoringStartedAt"
        @select="(id) => emit('select', id)"
        @hover="(id) => emit('hover', id)"
      />
    </Transition>
  </aside>
</template>
