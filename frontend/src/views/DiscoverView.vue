<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { useOpportunities } from '@/api/opportunities'
import OpportunityRadar from '@/components/radar/OpportunityRadar.vue'
import OpportunityRanking from '@/components/radar/OpportunityRanking.vue'
import RadarFootnote from '@/components/radar/RadarFootnote.vue'
import RadarHero from '@/components/radar/RadarHero.vue'
import RadarPreviewCard from '@/components/radar/RadarPreviewCard.vue'
import RadarStates, { RadarPlaceholder } from '@/components/radar/RadarStates.vue'
import { useAgentPeek } from '@/composables/useAgentPeek'
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
// El vistazo de Rad a un tema citado lo resalta como el hover, sin tocar la URL ni la selección.
watch(useAgentPeek().peekedId, (id) => (hovered.value = id))

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

  <div v-else-if="data" class="flex flex-col gap-4">
    <RadarHero
      :view
      :query
      :monitoring-started-at="data.monitoring_started_at"
      class="pt-5 pb-1"
      @select="select"
      @hover="hover"
    />

    <!-- Radar y ranking lado a lado para no hacer scroll: el ranking toma el alto del radar y
         desplaza sus filas dentro de su tarjeta. Al elegir un tema, su vista previa ocupa el sitio
         del ranking («‹ Ranking» vuelve). Por debajo de 1280 px se apilan. -->
    <div class="grid items-stretch gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
      <OpportunityRadar
        :view
        :hovered-id="hovered"
        :sweep-key="`${query.period}:${sweepCount}`"
        @select="select"
        @hover="hover"
      />
      <!-- DESIGN.md §7: cambia con fundido y 6 px de subida (280 ms). La vista previa no se
           remonta al cambiar de tema: así el anillo cuenta hasta el nuevo valor. -->
      <Transition
        mode="out-in"
        enter-from-class="translate-y-1.5 opacity-0"
        enter-active-class="transition duration-[280ms] ease-out motion-reduce:transition-none"
      >
        <RadarPreviewCard
          v-if="view.selected"
          :opportunity="view.selected"
          :total="view.total"
          @clear="clearSelection"
        />
        <OpportunityRanking
          v-else
          :rows="view.visible"
          :is-filtered="view.isFiltered"
          :selected-id="null"
          :hovered-id="hovered"
          @select="select"
          @hover="hover"
        />
      </Transition>
    </div>

    <RadarFootnote :monitoring-started-at="data.monitoring_started_at" />
  </div>
</template>
