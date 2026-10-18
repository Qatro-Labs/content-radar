<script setup lang="ts">
import { computed } from 'vue'

import HoverHint from '@/components/layout/HoverHint.vue'
import ViewHeader from '@/components/layout/ViewHeader.vue'
import { useRadarAgent } from '@/composables/useRadarAgent'
import { useRadarQuery } from '@/composables/useRadarQuery'
import { AGENT_ANCHOR, COUNTER_ANCHOR } from '@/lib/agentTargets'
import { HELP } from '@/lib/helpText'
import { LIFECYCLE_STYLE } from '@/lib/lifecycle'
import { RECOMMENDATION_LABEL } from '@/lib/opportunityFormat'
import { resetViewPatch, serializeRadarQuery, type RadarQuery } from '@/lib/radarQuery'
import {
  counterPatch,
  radarHeadline,
  radarSubline,
  type CounterFilter as CounterFilterName,
  type RadarView,
} from '@/lib/radarView'

import CounterFilter, { type CounterSwatch } from './CounterFilter.vue'

const { view, query } = defineProps<{
  view: RadarView
  query: RadarQuery
}>()

const { update } = useRadarQuery()
const { agentRadarParams } = useRadarAgent()

interface Counter {
  filter: CounterFilterName
  label: string
  count: number
  swatch: CounterSwatch
  // Objetivo del agente del Radar: el mismo control que pulsa una persona.
  agentTarget: string
  help: string
}

const counters = computed<Counter[]>(() => [
  {
    filter: 'publish_now',
    label: RECOMMENDATION_LABEL.publish_now,
    count: view.counts.publishNow,
    swatch: 'signal',
    agentTarget: COUNTER_ANCHOR.publish_now,
    help: HELP.counterPublishNow,
  },
  {
    filter: 'accelerating',
    label: LIFECYCLE_STYLE.accelerating.label,
    count: view.counts.accelerating,
    swatch: 'accelerating',
    agentTarget: COUNTER_ANCHOR.accelerating,
    help: HELP.counterAccelerating,
  },
  {
    filter: 'emerging',
    // En plural: cuenta temas, y el chip de etapa dice «Emergente».
    label: 'Emergentes',
    count: view.counts.emerging,
    swatch: 'emerging',
    agentTarget: COUNTER_ANCHOR.emerging,
    help: HELP.counterEmerging,
  },
])
// «Sin tendencia clara» no tiene contador: era la cifra más grande de la cabecera y solo dice lo
// que no sabemos. Sigue en la leyenda, en «Qué no sabemos» y en la URL (Rad puede filtrarla).

// Los resaltados también atenúan el radar, así que cuentan como vista cambiada y se
// restablecen con los filtros (artboard E).
const isViewChanged = computed(() => view.isFiltered || query.highlight.length > 0)
// DESIGN.md §4: si la vista es justo la que dejó Rad, se dice; en cuanto la persona toca un filtro,
// la URL cambia y la frase desaparece.
const isSetByRad = computed(
  () =>
    isViewChanged.value &&
    agentRadarParams.value === new URLSearchParams(serializeRadarQuery(query)).toString(),
)
</script>

<template>
  <section class="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
    <!-- La frase se parte antes que bajar los contadores a otra fila: cada línea cuenta para
         que el Radar quepa en la ventana. -->
    <ViewHeader class="min-w-0 flex-[1_1_420px]" :title="radarHeadline(view, query)">
      {{ radarSubline(view, query) }}
    </ViewHeader>

    <div class="flex flex-wrap items-center gap-2">
      <div role="group" aria-label="Filtrar por" class="flex flex-wrap gap-2">
        <HoverHint v-for="counter in counters" :key="counter.filter" :text="counter.help">
          <CounterFilter
            :data-agent="counter.agentTarget"
            :count="counter.count"
            :label="counter.label"
            :swatch="counter.swatch"
            :pressed="view.activeCounter === counter.filter"
            @click="update(counterPatch(counter.filter, query))"
          />
        </HoverHint>
      </div>

      <span v-if="isSetByRad" class="text-[13.5px] text-muted-foreground">
        Filtros puestos por Rad
      </span>
      <Transition
        enter-from-class="translate-y-1 opacity-0"
        enter-active-class="transition duration-300 ease-out motion-reduce:transition-none"
      >
        <HoverHint v-if="isViewChanged" :text="HELP.resetView">
          <button
            type="button"
            :data-agent="AGENT_ANCHOR.reset"
            class="min-h-11 rounded-xl bg-card px-4 text-sm font-semibold transition-[background-color,scale] duration-150 ease-out hover:bg-secondary-hover active:scale-[0.98]"
            @click="update(resetViewPatch())"
          >
            Restablecer vista
          </button>
        </HoverHint>
      </Transition>
    </div>
  </section>
</template>
