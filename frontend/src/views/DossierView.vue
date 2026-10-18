<script setup lang="ts">
import { computed, type ComputedRef, type Ref, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import {
  type QueryState,
  useOpportunities,
  useOpportunity,
  useOpportunityEvidence,
  useOpportunityTimeline,
} from '@/api/opportunities'
import DossierActions from '@/components/dossier/DossierActions.vue'
import DossierEvolution from '@/components/dossier/DossierEvolution.vue'
import DossierHeader from '@/components/dossier/DossierHeader.vue'
import DossierStates, { DossierPlaceholder } from '@/components/dossier/DossierStates.vue'
import DossierSummary from '@/components/dossier/DossierSummary.vue'
import EvidenceSection from '@/components/dossier/EvidenceSection.vue'
import FitSection from '@/components/dossier/FitSection.vue'
import ScoreComposition from '@/components/dossier/ScoreComposition.vue'
import { rankLabel, rankOf } from '@/lib/dossierView'
import { formatUtcTimestamp } from '@/lib/format'
import { DEFAULT_PERIOD } from '@/lib/radarQuery'
import type { components } from '@/types/api'

type Schemas = components['schemas']

interface QueryRefs<T> {
  data: Ref<T | undefined>
  isPending: Ref<boolean>
  isError: Ref<boolean>
}

// Cada sección recibe el estado de su consulta, no el objeto de TanStack Query.
function toQueryState<T>(query: QueryRefs<T>): ComputedRef<QueryState<T>> {
  return computed(() => ({
    data: query.data.value,
    isPending: query.isPending.value,
    isError: query.isError.value,
  }))
}

const route = useRoute()
const id = computed(() => String(route.params.id))

const opportunityQuery = useOpportunity(id)
const timelineQuery = useOpportunityTimeline(id)
const evidenceQuery = useOpportunityEvidence(id)
// La lista solo da el puesto y desde cuándo se monitorea: si falla, el expediente sigue en pie.
const listQuery = useOpportunities(DEFAULT_PERIOD)

const opportunity = computed(() => opportunityQuery.data.value ?? null)
const timeline = toQueryState<Schemas['OpportunityTimeline'] | null>(timelineQuery)
const evidence = toQueryState<Schemas['Evidence'][]>(evidenceQuery)

const placeholder = computed<DossierPlaceholder | null>(() => {
  if (opportunityQuery.isPending.value) return DossierPlaceholder.Loading
  if (opportunityQuery.isError.value) return DossierPlaceholder.Error
  if (opportunity.value === null) return DossierPlaceholder.NotFound
  return null
})

const citablePieces = computed(() => evidence.value.data ?? [])

// D11: la pieza citada que se resalta es estado local, no va en la URL.
const citedUrl = ref<string | null>(null)
watch(id, () => {
  citedUrl.value = null
})

function cite(url: string | null) {
  citedUrl.value = url
}

const rankText = computed(() =>
  listQuery.isPending.value ? null : rankLabel(rankOf(listQuery.data.value, id.value)),
)
const monitoringStartedAt = computed(() => listQuery.data.value?.monitoring_started_at ?? null)
</script>

<template>
  <DossierStates v-if="placeholder" :state="placeholder" @retry="opportunityQuery.refetch()" />

  <div v-else-if="opportunity" class="flex flex-col gap-4">
    <!-- Primero qué hacer y por qué (cabecera, acción, resumen y «Qué no sabemos»); después el
         detalle: evolución, encaje, evidencia y, plegado, cómo se calcula el score. -->
    <div class="flex flex-wrap items-start gap-4 pt-3">
      <DossierHeader :opportunity />
      <DossierActions :opportunity :rank-text="rankText" />
    </div>
    <DossierSummary :opportunity :timeline />
    <DossierEvolution :opportunity :timeline />
    <FitSection :opportunity :evidence="citablePieces" :cited-url="citedUrl" @cite="cite" />
    <EvidenceSection
      :opportunity
      :evidence
      :cited-url="citedUrl"
      @retry="evidenceQuery.refetch()"
    />
    <ScoreComposition :opportunity :rank-text="rankText" />

    <!-- DESIGN.md §9: desde cuándo se monitorea va siempre a la vista, y el encaje y la saturación
         se rotulan para que no se lean como mediciones absolutas (CLAUDE.md §2.3). -->
    <p class="px-1 text-[13.5px] text-muted-foreground">
      <template v-if="monitoringStartedAt">
        Datos desde el {{ formatUtcTimestamp(monitoringStartedAt) }}.
      </template>
      La saturación se mide dentro de las fuentes monitoreadas. El encaje es una evaluación
      editorial, no una medición. Los enlaces abren la pieza original.
    </p>
  </div>
</template>
