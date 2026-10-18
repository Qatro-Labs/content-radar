<script setup lang="ts">
import { Search } from '@lucide/vue'
import { ListboxFilter } from 'reka-ui'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter, type RouteLocationRaw } from 'vue-router'

import { useAllEvidence, useOpportunities } from '@/api/opportunities'
import StageDot from '@/components/explore/StageDot.vue'
import { Command, CommandGroup, CommandItem, CommandList } from '@/components/ui/command'
import { DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { countLabel, PLATFORM_LABEL } from '@/lib/evidenceFormat'
import { EXPLORE_TEXT_PARAM } from '@/lib/exploreView'
import { formatScore } from '@/lib/opportunityFormat'
import { DEFAULT_PERIOD } from '@/lib/radarQuery'
import { buildSearchResults, hasResults, topicDestination } from '@/lib/searchPalette'
import { RouteName } from '@/router'

const open = defineModel<boolean>('open', { required: true })

const route = useRoute()
const router = useRouter()
const text = ref('')

const {
  data: list,
  isPending: isTopicsPending,
  isError: isTopicsError,
} = useOpportunities(DEFAULT_PERIOD)
const opportunities = computed(() => list.value?.items ?? [])
// Las piezas se piden al abrir la paleta: al cargar la app todavía no hacen falta.
const {
  data: evidence,
  isPending: isPiecesPending,
  isError: isPiecesError,
} = useAllEvidence(() => open.value)

const results = computed(() =>
  buildSearchResults({
    opportunities: opportunities.value,
    evidence: evidence.value ?? [],
    text: text.value,
  }),
)
const isLoading = computed(() => isTopicsPending.value || isPiecesPending.value)
const showPieces = computed(() => !isLoading.value)

const statusLine = computed<string | null>(() => {
  if (isTopicsError.value) return 'No se pudieron cargar los temas.'
  if (list.value === null) return 'Todavía no hay análisis: el job analyze no ha corrido.'
  if (isTopicsPending.value) return 'Cargando temas…'
  if (isPiecesPending.value) return 'Cargando piezas…'
  if (isPiecesError.value && evidence.value === undefined) return 'No se pudo cargar la evidencia.'
  return null
})
// Sin temas cargados, "ningún tema coincide" se leería como un resultado (CLAUDE.md §2.3).
const showNoMatches = computed(
  () =>
    list.value != null &&
    !isLoading.value &&
    text.value.trim() !== '' &&
    !hasResults(results.value),
)

watch(open, (isOpen) => {
  if (!isOpen) text.value = ''
})

function go(to: RouteLocationRaw) {
  open.value = false
  void router.push(to)
}

// En Crear, un tema o una pieza abren el brief de su tema; en el resto, su expediente.
function openTopic(id: string) {
  go(topicDestination(route.name, id))
}

function openSourceInExplore(source: string) {
  go({ name: RouteName.Explore, query: { [EXPLORE_TEXT_PARAM]: source } })
}

// El check de CommandItem marca opciones elegidas; aquí cada opción navega, así que se oculta.
const ITEM_CLASS =
  'min-h-11 gap-3 px-3 py-2 text-[15px] data-highlighted:bg-secondary [&>svg:last-child]:hidden'
const GROUP_CLASS =
  'p-0 pt-2 **:data-[slot=command-group-heading]:px-3 **:data-[slot=command-group-heading]:pb-1.5 **:data-[slot=command-group-heading]:text-[13px] **:data-[slot=command-group-heading]:font-medium **:data-[slot=command-group-heading]:text-muted-foreground'
const META_CLASS = 'truncate text-[13px] text-muted-foreground'
</script>

<template>
  <DialogContent
    :show-close-button="false"
    class="top-[12dvh] translate-y-0 gap-0 overflow-hidden p-0 sm:max-w-[640px]"
  >
    <DialogTitle class="sr-only">Buscar tema o pieza</DialogTitle>
    <DialogDescription class="sr-only">
      Temas, piezas y fuentes del análisis servido. Al elegir uno, se abre su vista.
    </DialogDescription>

    <!-- El filtrado es de buildSearchResults: el campo no pasa por el filtro interno de Command,
         que solo compara el texto visible de cada opción. -->
    <Command class="rounded-none! p-0">
      <label
        class="m-3 flex h-12 items-center gap-2.5 rounded-xl bg-secondary px-3.5 focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ring"
      >
        <Search
          class="size-4 shrink-0 text-muted-foreground"
          :stroke-width="2"
          aria-hidden="true"
        />
        <span class="sr-only">Buscar tema, pieza o fuente</span>
        <ListboxFilter
          v-model="text"
          auto-focus
          placeholder="Buscar tema, pieza o fuente"
          class="min-w-0 flex-1 bg-transparent text-[15px] text-foreground placeholder:text-muted-foreground focus-visible:outline-none"
        />
      </label>

      <CommandList class="max-h-[min(60dvh,480px)] px-2 pb-2">
        <CommandGroup v-if="results.topics.length > 0" heading="Temas" :class="GROUP_CLASS">
          <CommandItem
            v-for="topic in results.topics"
            :key="topic.id"
            :value="`topic:${topic.id}`"
            :class="ITEM_CLASS"
            @select="openTopic(topic.id)"
          >
            <StageDot :lifecycle="topic.lifecycle" />
            <span class="min-w-0 flex-1 truncate font-medium">{{ topic.topic }}</span>
            <span class="shrink-0 text-[13px] text-muted-foreground">
              Oportunidad
              <span :class="topic.opportunity_score == null ? '' : 'font-semibold text-foreground'">
                {{ formatScore(topic.opportunity_score) }}
              </span>
            </span>
          </CommandItem>
        </CommandGroup>

        <CommandGroup
          v-if="showPieces && results.pieces.length > 0"
          heading="Piezas"
          :class="GROUP_CLASS"
        >
          <CommandItem
            v-for="piece in results.pieces"
            :key="piece.url"
            :value="`piece:${piece.url}`"
            :class="ITEM_CLASS"
            @select="openTopic(piece.opportunity.id)"
          >
            <span class="flex min-w-0 flex-1 flex-col">
              <span class="truncate font-medium">{{ piece.title }}</span>
              <span :class="META_CLASS">
                {{ piece.source }} · {{ PLATFORM_LABEL[piece.platform] }}
              </span>
            </span>
          </CommandItem>
        </CommandGroup>

        <CommandGroup
          v-if="showPieces && results.sources.length > 0"
          heading="Fuentes"
          :class="GROUP_CLASS"
        >
          <CommandItem
            v-for="entry in results.sources"
            :key="entry.source"
            :value="`source:${entry.source}`"
            :class="ITEM_CLASS"
            @select="openSourceInExplore(entry.source)"
          >
            <span class="min-w-0 flex-1 truncate font-medium">{{ entry.source }}</span>
            <span :class="META_CLASS" class="shrink-0">
              {{ countLabel(entry.pieceCount, 'pieza', 'piezas') }}
            </span>
          </CommandItem>
        </CommandGroup>
      </CommandList>

      <p v-if="statusLine" class="px-5 pb-4 text-sm text-muted-foreground">{{ statusLine }}</p>
      <p v-if="showNoMatches" class="px-5 pt-2 pb-6 text-[15px] text-ink-soft">
        Ningún tema, pieza o fuente coincide con «{{ text.trim() }}».
      </p>
    </Command>
  </DialogContent>
</template>
