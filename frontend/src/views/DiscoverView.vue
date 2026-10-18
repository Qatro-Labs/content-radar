<script setup lang="ts">
import { usePreferredReducedMotion } from '@vueuse/core'
import { type ComponentPublicInstance, computed, nextTick, ref, useTemplateRef, watch } from 'vue'

import { useOpportunities } from '@/api/opportunities'
import OpportunityRadar from '@/components/radar/OpportunityRadar.vue'
import OpportunityRanking from '@/components/radar/OpportunityRanking.vue'
import RadarFootnote from '@/components/radar/RadarFootnote.vue'
import RadarHero from '@/components/radar/RadarHero.vue'
import RadarSidePanel from '@/components/radar/RadarSidePanel.vue'
import RadarStates, { RadarPlaceholder } from '@/components/radar/RadarStates.vue'
import { useRadarAgent } from '@/composables/useRadarAgent'
import { useRadarQuery } from '@/composables/useRadarQuery'
import { buildRadarView } from '@/lib/radarView'

const { query, update } = useRadarQuery()
// Rad repite el barrido cuando empieza a leer datos (DESIGN.md §7).
const { sweepCount } = useRadarAgent()
const { data, isPending, isError, refetch } = useOpportunities(() => query.value.period)

const view = computed(() => buildRadarView(data.value ?? null, query.value))
// El hover enlaza radar, ranking y panel, pero no va en la URL: no es un estado que se comparta.
const hovered = ref<string | null>(null)

// Sin una lista con temas no se monta la cabecera: "0 temas esta semana" se leería como un
// resultado real (CLAUDE.md §2.3).
const placeholder = computed<RadarPlaceholder | null>(() => {
  if (isPending.value) return RadarPlaceholder.Loading
  if (isError.value) return RadarPlaceholder.Error
  if (data.value === null) return RadarPlaceholder.NotAnalyzed
  if (view.value.total === 0) return RadarPlaceholder.Empty
  return null
})

// El hover se suelta al cambiar la selección: el panel cambia de estado bajo el cursor y la
// fila de «Esta semana» desaparece sin `mouseleave`, así que su tarjeta flotante se quedaría.
function changeSelection(id: string | null) {
  hovered.value = null
  update({ selected: id })
}

// El tema elegido se abre debajo del radar: si el panel queda fuera de la pantalla, la página baja
// lo justo para enseñarlo.
const panel = useTemplateRef<ComponentPublicInstance>('panel')
const reducedMotion = usePreferredReducedMotion()
watch(
  () => view.value.selected?.id,
  async (id) => {
    if (!id) return
    await nextTick()
    const element = panel.value?.$el
    if (!(element instanceof HTMLElement)) return
    element.scrollIntoView({
      block: 'nearest',
      behavior: reducedMotion.value === 'reduce' ? 'auto' : 'smooth',
    })
  },
)

// D7: elegir el tema ya seleccionado lo deselecciona.
function select(id: string) {
  changeSelection(view.value.selected?.id === id ? null : id)
}

function clearSelection() {
  changeSelection(null)
}

function hover(id: string | null) {
  hovered.value = id
}
</script>

<template>
  <RadarStates v-if="placeholder" :state="placeholder" @retry="refetch()" />

  <div v-else-if="data" class="flex flex-col gap-4">
    <RadarHero :view :query class="pt-5 pb-1" />

    <!-- Radar y ranking lado a lado para no hacer scroll: el ranking toma el alto del radar y
         desplaza sus filas dentro de su tarjeta. Por debajo de 1280 px se apilan. -->
    <div class="grid items-stretch gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
      <OpportunityRadar
        :view
        :hovered-id="hovered"
        :sweep-key="`${query.period}:${sweepCount}`"
        @select="select"
        @hover="hover"
      />
      <OpportunityRanking
        :rows="view.visible"
        :is-filtered="view.isFiltered"
        :selected-id="view.selected?.id ?? null"
        :hovered-id="hovered"
        @select="select"
        @hover="hover"
      />
    </div>

    <RadarSidePanel
      ref="panel"
      :view
      :monitoring-started-at="data.monitoring_started_at"
      @select="select"
      @hover="hover"
      @clear="clearSelection"
    />
    <RadarFootnote :monitoring-started-at="data.monitoring_started_at" />
  </div>
</template>
