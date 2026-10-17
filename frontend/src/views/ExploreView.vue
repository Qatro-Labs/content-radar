<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useOpportunities, useOpportunitiesEvidence } from '@/api/opportunities'
import ExploreHeader from '@/components/explore/ExploreHeader.vue'
import ExploreSidePanel from '@/components/explore/ExploreSidePanel.vue'
import ExploreSkeleton from '@/components/explore/ExploreSkeleton.vue'
import PiecesTable from '@/components/explore/PiecesTable.vue'
import { countLabel, PERFORMANCE_LEGEND } from '@/lib/evidenceFormat'
import {
  buildExploreView,
  EXPLORE_FILTER_PARAM,
  parseExploreFilter,
  type ExploreFilter,
} from '@/lib/exploreView'
import { formatUtcTimestamp } from '@/lib/format'
import { DEFAULT_PERIOD } from '@/lib/radarQuery'
import type { components } from '@/types/api'

type Evidence = components['schemas']['Evidence']

const route = useRoute()
const router = useRouter()

const { data: list, isPending, isError, refetch } = useOpportunities(DEFAULT_PERIOD)
const opportunities = computed(() => list.value?.items ?? [])
// No hay endpoint de todas las piezas: una petición a /evidence por tema (D5 del plan
// fe-dashboard-v2).
const { evidenceById, refetchFailed } = useOpportunitiesEvidence(() =>
  opportunities.value.map((opportunity) => opportunity.id),
)

const evidenceStates = computed(() => [...evidenceById.value.values()])
const isEvidencePending = computed(() => evidenceStates.value.some((state) => state.isPending))
const failedTopicCount = computed(
  () => evidenceStates.value.filter((state) => state.isError && state.data === undefined).length,
)
const loadedEvidence = computed(() => {
  const loaded = new Map<string, Evidence[]>()
  for (const [id, state] of evidenceById.value) {
    if (state.data !== undefined) loaded.set(id, state.data)
  }
  return loaded
})

const filter = computed(() => parseExploreFilter(route.query))
// El texto y la pieza elegida no van en la URL: no son un estado que se comparta.
const text = ref('')
const selectedUrl = ref<string | null>(null)

const view = computed(() =>
  buildExploreView({
    opportunities: opportunities.value,
    evidenceById: loadedEvidence.value,
    filter: filter.value,
    text: text.value,
  }),
)

// Mientras llegan las peticiones de cada tema, la tabla se reordenaría con cada una: se espera a
// que terminen todas.
const isLoading = computed(() => isPending.value || isEvidencePending.value)

const failedMessage = computed(
  () => `No se pudo cargar la evidencia de ${countLabel(failedTopicCount.value, 'tema', 'temas')}.`,
)

// Sin piezas cargadas no se monta la cabecera: "0 piezas de los 0 temas" se leería como un
// resultado real (CLAUDE.md §2.3).
const message = computed<string | null>(() => {
  if (isError.value) return 'No se pudieron cargar las oportunidades.'
  if (list.value === null) return 'Todavía no hay análisis: el job analyze no ha corrido.'
  if (opportunities.value.length === 0) {
    return 'El último análisis no encontró temas con datos suficientes.'
  }
  if (view.value.topicCount === 0) return failedMessage.value
  return null
})
const canRetry = computed(() => isError.value || failedTopicCount.value > 0)

function retry() {
  if (isError.value) void refetch()
  else refetchFailed()
}

// `replace` y no `push`, como en el Radar: cambiar un filtro no llena el historial.
function toggleFilter(clicked: ExploreFilter) {
  const next = filter.value === clicked ? undefined : clicked
  void router.replace({ query: { ...route.query, [EXPLORE_FILTER_PARAM]: next } })
}

// Se busca entre todas las piezas, no solo las filtradas: la pieza elegida sigue en el panel
// aunque un filtro la saque de la tabla.
const selectedPiece = computed(
  () => view.value.pieces.find((piece) => piece.url === selectedUrl.value) ?? null,
)

function toggleSelection(url: string) {
  selectedUrl.value = selectedUrl.value === url ? null : url
}

const RETRY_BUTTON =
  'min-h-11 rounded-xl bg-secondary px-4 text-sm font-semibold transition-[background-color,scale] duration-150 ease-out hover:bg-secondary-hover active:scale-[0.98]'
</script>

<template>
  <ExploreSkeleton v-if="isLoading" />

  <section
    v-else-if="message"
    aria-label="Piezas"
    class="flex flex-col gap-3 rounded-card bg-card p-6"
  >
    <h2 class="font-display text-[22px] leading-tight font-semibold tracking-[-0.02em]">Piezas</h2>
    <div class="flex flex-wrap items-center gap-x-4 gap-y-3">
      <p class="text-[17px] leading-[1.55] text-ink-soft">{{ message }}</p>
      <button v-if="canRetry" type="button" :class="RETRY_BUTTON" @click="retry">Reintentar</button>
    </div>
  </section>

  <div v-else-if="list" class="flex flex-col gap-4">
    <ExploreHeader :view :filter class="pt-5 pb-1" @toggle="toggleFilter" />

    <div class="flex flex-wrap items-start gap-4">
      <div class="flex min-w-0 flex-[999_1_720px] flex-col gap-4">
        <!-- DESIGN.md §4: el error va en línea y el resto de los temas se sigue mostrando. -->
        <div
          v-if="failedTopicCount > 0"
          class="flex flex-wrap items-center gap-x-4 gap-y-3 rounded-card bg-card px-6 py-4"
        >
          <p role="alert" class="text-[15px] text-ink-soft">{{ failedMessage }}</p>
          <button type="button" :class="RETRY_BUTTON" @click="refetchFailed">Reintentar</button>
        </div>

        <PiecesTable
          v-model:text="text"
          :rows="view.visible"
          :filter
          :selected-url="selectedUrl"
          @select="toggleSelection"
        />

        <!-- DESIGN.md §9: desde cuándo se monitorea va siempre a la vista. -->
        <p class="px-1 text-[13.5px] text-muted-foreground">
          Datos desde el {{ formatUtcTimestamp(list.monitoring_started_at) }}.
          {{ PERFORMANCE_LEGEND }}
        </p>
      </div>

      <ExploreSidePanel :view :selected="selectedPiece" @clear="selectedUrl = null" />
    </div>
  </div>
</template>
