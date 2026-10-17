<script setup lang="ts">
import { computed, ref } from 'vue'

import { useOpportunities } from '@/api/opportunities'
import AudienceMixCard from '@/components/radar/AudienceMixCard.vue'
import OpportunityRadar from '@/components/radar/OpportunityRadar.vue'
import OpportunityRanking from '@/components/radar/OpportunityRanking.vue'
import RadarFilters from '@/components/radar/RadarFilters.vue'
import RadarFootnote from '@/components/radar/RadarFootnote.vue'
import RadarHero from '@/components/radar/RadarHero.vue'
import RadarSidePanel from '@/components/radar/RadarSidePanel.vue'
import RadarStates, { RadarPlaceholder } from '@/components/radar/RadarStates.vue'
import WhyItMattersCard from '@/components/radar/WhyItMattersCard.vue'
import { useRadarQuery } from '@/composables/useRadarQuery'
import { buildRadarView } from '@/lib/radarView'

const { query, update } = useRadarQuery()
const { data, isPending, isError, refetch } = useOpportunities(() => query.value.period)

const view = computed(() => buildRadarView(data.value ?? null, query.value))
// El hover enlaza radar y ranking, pero no va en la URL: no es un estado que se comparta.
const hovered = ref<string | null>(null)

// Sin una lista con temas no se monta la cabecera: "0 oportunidades esta semana" se leería como
// un resultado real (CLAUDE.md §2.3).
const placeholder = computed<RadarPlaceholder | null>(() => {
  if (isPending.value) return RadarPlaceholder.Loading
  if (isError.value) return RadarPlaceholder.Error
  if (data.value === null) return RadarPlaceholder.NotAnalyzed
  if (view.value.total === 0) return RadarPlaceholder.Empty
  return null
})

function select(id: string) {
  update({ selected: id })
}

function hover(id: string | null) {
  hovered.value = id
}
</script>

<template>
  <RadarStates v-if="placeholder" :state="placeholder" @retry="refetch()" />

  <div v-else-if="data && view.selected" class="flex flex-col gap-4">
    <RadarHero :view :query class="pt-5 pb-1" />
    <RadarFilters :view />

    <div class="flex flex-wrap items-stretch gap-4">
      <OpportunityRadar
        class="flex-[999_1_680px]"
        :view
        :hovered-id="hovered"
        :sweep-key="query.period"
        @select="select"
        @hover="hover"
      />
      <RadarSidePanel
        :view
        :monitoring-started-at="data.monitoring_started_at"
        @select="select"
        @hover="hover"
        @clear="update({ selected: null })"
      />
    </div>

    <div class="flex flex-wrap gap-4">
      <AudienceMixCard class="flex-[1_1_360px]" :opportunity="view.selected" />
      <WhyItMattersCard class="flex-[2_1_520px]" :opportunity="view.selected" />
    </div>

    <OpportunityRanking
      :rows="view.visible"
      :total="view.total"
      :is-filtered="view.isFiltered"
      :selected-id="view.selected.id"
      :hovered-id="hovered"
      @select="select"
      @hover="hover"
    />

    <RadarFootnote :monitoring-started-at="data.monitoring_started_at" />
  </div>
</template>
