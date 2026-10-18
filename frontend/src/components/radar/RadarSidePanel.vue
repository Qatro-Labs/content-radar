<script setup lang="ts">
import { computed } from 'vue'

import type { RadarView, RankedOpportunity } from '@/lib/radarView'

import OpportunityPreview from './OpportunityPreview.vue'
import WeekSummary from './WeekSummary.vue'

const { view, peeked, monitoringStartedAt } = defineProps<{
  view: RadarView
  // El tema citado por el que pasa el vistazo de Rad: se ve mientras dura, sin seleccionarlo.
  peeked: RankedOpportunity | null
  monitoringStartedAt: string
}>()

const emit = defineEmits<{
  select: [id: string]
  hover: [id: string | null]
  clear: []
}>()

const previewed = computed(() => peeked ?? view.selected)
</script>

<template>
  <!-- DESIGN.md §4: siempre a la vista. En escritorio toma el alto de la fila y desplaza su
       contenido dentro; en móvil, sticky mientras se baja. -->
  <aside
    aria-label="Panel del tema"
    class="sticky top-4 flex min-w-0 flex-[1_1_360px] flex-col self-start rounded-card bg-card p-[22px] lg:static lg:min-h-0 lg:self-stretch lg:overflow-y-auto"
  >
    <!-- DESIGN.md §7: cambia de estado con fundido y 6 px de subida (280 ms). La vista previa no
         se remonta al cambiar de tema: así el anillo cuenta hasta el nuevo valor. -->
    <Transition
      mode="out-in"
      enter-from-class="translate-y-1.5 opacity-0"
      enter-active-class="transition duration-[280ms] ease-out motion-reduce:transition-none"
    >
      <OpportunityPreview
        v-if="previewed"
        :opportunity="previewed"
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
