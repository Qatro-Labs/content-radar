<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { useOpportunities } from '@/api/opportunities'
import OpportunityRadar from '@/components/radar/OpportunityRadar.vue'
import OpportunityRanking from '@/components/radar/OpportunityRanking.vue'
import RadarFootnote from '@/components/radar/RadarFootnote.vue'
import RadarHero from '@/components/radar/RadarHero.vue'
import RadarSidePanel from '@/components/radar/RadarSidePanel.vue'
import RadarStates, { RadarPlaceholder } from '@/components/radar/RadarStates.vue'
import RadarTabs, { TAB_PANEL_ID, tabId } from '@/components/radar/RadarTabs.vue'
import { useAgentPeek } from '@/composables/useAgentPeek'
import { AGENT_ANCHOR } from '@/lib/agentTargets'
import { useRadarAgent } from '@/composables/useRadarAgent'
import { useRadarQuery } from '@/composables/useRadarQuery'
import { buildRadarView, RADAR_TOP, stagePatch } from '@/lib/radarView'

const { query, update } = useRadarQuery()
// Rad repite el barrido cuando empieza a leer datos (DESIGN.md §7).
const { sweepCount } = useRadarAgent()
const { data, isPending, isError, refetch } = useOpportunities(() => query.value.period)

// «Ver todos» en el radar: una preferencia de la sesión, no un estado que se comparta por URL.
const showsAllBubbles = ref(false)
const view = computed(() =>
  buildRadarView(data.value ?? null, query.value, {
    radarTop: showsAllBubbles.value ? null : RADAR_TOP,
  }),
)
// El hover enlaza radar, ranking y panel, pero no va en la URL: no es un estado que se comparta.
const hovered = ref<string | null>(null)
// El vistazo de Rad a un tema citado lo resalta como el hover y enseña su vista previa en el
// panel, sin tocar la URL ni la selección.
const { peekedId } = useAgentPeek()
watch(peekedId, (id) => (hovered.value = id))
const peeked = computed(
  () => view.value.ranked.find((topic) => topic.id === peekedId.value) ?? null,
)

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

  <div v-else-if="data" class="flex flex-col gap-4 lg:h-full">
    <RadarHero :view :query class="shrink-0 pt-2" />

    <!-- En escritorio la página no hace scroll: radar, ranking y panel llenan el alto que queda y
         lo que no cabe se desplaza dentro de su tarjeta. Con una ventana muy baja la fila guarda
         440 px y la página vuelve a hacer scroll, antes que aplastar el radar. -->
    <div
      class="flex flex-wrap items-start gap-4 lg:min-h-[440px] lg:flex-1 lg:flex-nowrap lg:items-stretch"
    >
      <div class="flex min-w-0 flex-[999_1_720px] flex-col gap-3 lg:min-h-0">
        <!-- Radar y ranking son la misma lista en dos formas: una pestaña elige cuál ocupa el
             área grande; filtros, selección y panel se mantienen. Es el bloque principal de Rad. -->
        <div
          :id="TAB_PANEL_ID"
          :data-agent="AGENT_ANCHOR.radar"
          role="tabpanel"
          :aria-labelledby="tabId(query.tab)"
          class="flex flex-col lg:min-h-0 lg:flex-1"
        >
          <OpportunityRadar
            v-if="query.tab === 'radar'"
            :view
            :hovered-id="hovered"
            :sweep-key="`${query.period}:${sweepCount}`"
            :shows-all="showsAllBubbles"
            :shows-hover-card="peekedId === null"
            @select="select"
            @hover="hover"
            @toggle-all="showsAllBubbles = !showsAllBubbles"
            @filter-stage="(stage) => update(stagePatch(stage, query))"
          >
            <template #title><RadarTabs /></template>
          </OpportunityRadar>
          <OpportunityRanking
            v-else
            :rows="view.visible"
            :is-filtered="view.isFiltered"
            :selected-id="view.selected?.id ?? null"
            :hovered-id="hovered"
            @select="select"
            @hover="hover"
          >
            <template #title><RadarTabs /></template>
          </OpportunityRanking>
        </div>
        <RadarFootnote class="shrink-0" :monitoring-started-at="data.monitoring_started_at" />
      </div>

      <RadarSidePanel
        :view
        :peeked
        :monitoring-started-at="data.monitoring_started_at"
        @select="select"
        @hover="hover"
        @clear="clearSelection"
      />
    </div>
  </div>
</template>
