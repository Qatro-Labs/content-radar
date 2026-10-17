<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import {
  type QueryState,
  useOpportunities,
  useOpportunity,
  useOpportunityTimeline,
} from '@/api/opportunities'
import DossierEvolution from '@/components/dossier/DossierEvolution.vue'
import DossierHeader from '@/components/dossier/DossierHeader.vue'
import DossierStates, { DossierPlaceholder } from '@/components/dossier/DossierStates.vue'
import ScoreComposition from '@/components/dossier/ScoreComposition.vue'
import { rankLabel, rankOf } from '@/lib/dossierView'
import { DEFAULT_PERIOD } from '@/lib/radarQuery'
import type { components } from '@/types/api'

type OpportunityTimeline = components['schemas']['OpportunityTimeline']

const route = useRoute()
const id = computed(() => String(route.params.id))

const opportunityQuery = useOpportunity(id)
const timelineQuery = useOpportunityTimeline(id)
// La lista solo da el puesto y desde cuándo se monitorea: si falla, el expediente sigue en pie.
const listQuery = useOpportunities(DEFAULT_PERIOD)

const opportunity = computed(() => opportunityQuery.data.value ?? null)
const timeline = computed<QueryState<OpportunityTimeline | null>>(() => ({
  data: timelineQuery.data.value,
  isPending: timelineQuery.isPending.value,
  isError: timelineQuery.isError.value,
}))

const placeholder = computed<DossierPlaceholder | null>(() => {
  if (opportunityQuery.isPending.value) return DossierPlaceholder.Loading
  if (opportunityQuery.isError.value) return DossierPlaceholder.Error
  if (opportunity.value === null) return DossierPlaceholder.NotFound
  return null
})

const rankText = computed(() =>
  listQuery.isPending.value ? null : rankLabel(rankOf(listQuery.data.value, id.value)),
)
</script>

<template>
  <DossierStates v-if="placeholder" :state="placeholder" @retry="opportunityQuery.refetch()" />

  <div v-else-if="opportunity" class="flex flex-col gap-4">
    <div class="flex flex-wrap items-stretch gap-4 pt-3">
      <DossierHeader :opportunity />
      <ScoreComposition :opportunity :rank-text="rankText" />
    </div>
    <DossierEvolution :opportunity :timeline />
  </div>
</template>
