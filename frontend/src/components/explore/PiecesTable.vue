<script setup lang="ts">
import { Search } from '@lucide/vue'
import { computed, ref, watch } from 'vue'

import { formatCount } from '@/lib/evidenceFormat'
import type { ExploreFilter, Piece } from '@/lib/exploreView'

import PieceRow, { PIECES_GRID_CLASS } from './PieceRow.vue'

const { rows, total, filter, selectedUrl } = defineProps<{
  // Las piezas que pasan el filtro y el texto, ya ordenadas.
  rows: Piece[]
  total: number
  filter: ExploreFilter | null
  selectedUrl: string | null
}>()

const text = defineModel<string>('text', { required: true })

const emit = defineEmits<{ select: [url: string] }>()

const COLUMNS = ['Pieza', 'Tema', 'Plataforma', 'Publicada', 'Rendimiento'] as const

// Cientos de piezas no caben de una vez: se muestran de 25 en 25, y al cambiar el filtro o el
// texto se vuelve a las 25 primeras.
const PAGE_SIZE = 25
const limit = ref(PAGE_SIZE)
watch([() => filter, text], () => {
  limit.value = PAGE_SIZE
})

const shownRows = computed(() => rows.slice(0, limit.value))
const nextPageSize = computed(() => Math.min(PAGE_SIZE, rows.length - limit.value))
const isFiltered = computed(() => filter !== null || text.value.trim() !== '')

function showMore() {
  limit.value += PAGE_SIZE
}
</script>

<template>
  <section
    aria-label="Piezas"
    class="flex min-w-0 flex-col gap-1 rounded-card bg-card px-5 pt-5 pb-3"
  >
    <div class="flex flex-wrap items-center justify-between gap-3 px-1 pb-2">
      <h2 class="font-display text-[22px] font-semibold tracking-[-0.02em]">
        Piezas
        <span class="ml-1 font-sans text-sm font-medium tracking-normal text-muted-foreground">
          mostrando {{ formatCount(rows.length) }} de {{ formatCount(total) }}
        </span>
      </h2>
      <label
        class="flex min-h-11 items-center gap-2 rounded-[10px] bg-secondary px-3 text-sm focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ring"
      >
        <Search
          class="size-4 shrink-0 text-muted-foreground"
          :stroke-width="2"
          aria-hidden="true"
        />
        <span class="sr-only">Filtrar por título o fuente</span>
        <input
          v-model="text"
          type="search"
          placeholder="Filtrar por título o fuente"
          class="w-[220px] min-w-0 bg-transparent text-foreground placeholder:text-muted-foreground focus-visible:outline-none"
        />
      </label>
    </div>

    <p v-if="rows.length === 0" class="px-1 py-6 text-[15px] text-ink-soft">
      {{
        isFiltered
          ? 'Ninguna pieza cumple estos filtros.'
          : 'Todavía no hay piezas en la evidencia servida.'
      }}
    </p>

    <div v-else class="overflow-x-auto">
      <div class="min-w-[900px]">
        <div class="py-1.5 text-[13px] text-muted-foreground" :class="PIECES_GRID_CLASS">
          <span v-for="column in COLUMNS" :key="column">{{ column }}</span>
        </div>
        <PieceRow
          v-for="piece in shownRows"
          :key="piece.url"
          :piece
          :selected="piece.url === selectedUrl"
          @select="(url) => emit('select', url)"
        />
      </div>
    </div>

    <button
      v-if="nextPageSize > 0"
      type="button"
      class="mx-1 mt-2 mb-1 min-h-11 self-start rounded-xl bg-secondary px-4 text-sm font-semibold transition-[background-color,scale] duration-150 ease-out hover:bg-secondary-hover active:scale-[0.98]"
      @click="showMore"
    >
      Ver {{ nextPageSize }} más
    </button>
  </section>
</template>
