<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAllEvidence, useOpportunities } from '@/api/opportunities'
import ExploreHeader from '@/components/explore/ExploreHeader.vue'
import ExploreSidePanel from '@/components/explore/ExploreSidePanel.vue'
import ExploreSkeleton from '@/components/explore/ExploreSkeleton.vue'
import PiecesTable from '@/components/explore/PiecesTable.vue'
import { countLabel, PERFORMANCE_LEGEND } from '@/lib/evidenceFormat'
import {
  buildExploreView,
  EXPLORE_FILTER_PARAM,
  EXPLORE_TEXT_PARAM,
  parseExploreFilter,
  parseExploreText,
  type ExploreFilter,
} from '@/lib/exploreView'
import { formatUtcTimestamp } from '@/lib/format'
import { DEFAULT_PERIOD } from '@/lib/radarQuery'

const route = useRoute()
const router = useRouter()

const { data: list, isPending, isError, refetch } = useOpportunities(DEFAULT_PERIOD)
const opportunities = computed(() => list.value?.items ?? [])
const {
  data: evidence,
  isPending: isEvidencePending,
  isError: isEvidenceQueryError,
  refetch: refetchEvidence,
} = useAllEvidence()
// Si falla una recarga en segundo plano, las piezas que ya llegaron se siguen mostrando.
const isEvidenceError = computed(() => isEvidenceQueryError.value && evidence.value === undefined)

const filter = computed(() => parseExploreFilter(route.query))
// El texto va en la URL (`q`) para que la paleta ⌘K abra Explorar con una fuente ya filtrada.
// Se escribe tal cual, sin recortar: si no, el espacio entre dos palabras se borraría al teclearlo.
const text = computed({
  get: () => parseExploreText(route.query),
  set: (value: string) => {
    void router.replace({
      query: { ...route.query, [EXPLORE_TEXT_PARAM]: value === '' ? undefined : value },
    })
  },
})
// La pieza elegida no va en la URL: no es un estado que se comparta.
const selectedUrl = ref<string | null>(null)

const view = computed(() =>
  buildExploreView({
    opportunities: opportunities.value,
    evidence: evidence.value ?? [],
    filter: filter.value,
    text: text.value,
  }),
)

const isLoading = computed(() => isPending.value || isEvidencePending.value)

// Sin piezas no se monta la cabecera: "0 piezas de los 0 temas" se leería como un resultado real
// (CLAUDE.md §2.3).
const message = computed<string | null>(() => {
  if (isError.value) return 'No se pudieron cargar las oportunidades.'
  if (list.value === null) return 'Todavía no hay análisis: el job analyze no ha corrido.'
  if (opportunities.value.length === 0) {
    return 'El último análisis no encontró temas con datos suficientes.'
  }
  if (isEvidenceError.value) return 'No se pudo cargar la evidencia.'
  if (view.value.topicsWithPiecesCount === 0)
    return 'El último análisis no trae piezas de evidencia.'
  return null
})
const canRetry = computed(() => isError.value || isEvidenceError.value)

function retry() {
  if (isError.value) void refetch()
  if (isEvidenceError.value) void refetchEvidence()
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
          <template v-if="view.counts.rss > 0">
            RSS ({{ countLabel(view.counts.rss, 'pieza', 'piezas') }}) no publica métricas: sus
            piezas se cuentan, pero no se comparan.
          </template>
        </p>
      </div>

      <ExploreSidePanel :view :selected="selectedPiece" @clear="selectedUrl = null" />
    </div>
  </div>
</template>
