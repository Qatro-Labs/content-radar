<script lang="ts">
// Tres columnas: plataforma, fuente y fecha van bajo el título, y la cifra frente a su canal no
// lleva barra (la barra se queda en el detalle de la pieza, donde se explica). Por debajo de unos
// 620 px la tabla hace scroll dentro de su tarjeta (DESIGN.md §6). La cabecera de PiecesTable
// comparte la rejilla.
export const PIECES_GRID_CLASS =
  'grid grid-cols-[minmax(280px,2.4fr)_minmax(170px,1.2fr)_112px] items-center gap-x-3.5 px-3.5'
</script>

<script setup lang="ts">
import { formatRatio, missingRatioLabel, PLATFORM_LABEL } from '@/lib/evidenceFormat'
import type { Piece } from '@/lib/exploreView'
import { formatUtcDay } from '@/lib/format'

import StageDot from './StageDot.vue'

const { piece, selected } = defineProps<{ piece: Piece; selected: boolean }>()

const emit = defineEmits<{ select: [url: string] }>()
</script>

<template>
  <!-- DESIGN.md §2 y §4: la seleccionada en lavado de señal (0.18) y el hover en Superficie
       hundida, como las filas del ranking. -->
  <button
    type="button"
    :aria-pressed="selected"
    class="min-h-[58px] w-full border-t border-table-line py-1.5 text-left text-[14.5px] transition-colors duration-150 ease-out"
    :class="[PIECES_GRID_CLASS, selected ? 'bg-signal/18' : 'bg-card hover:bg-sunken']"
    @click="emit('select', piece.url)"
  >
    <span class="flex min-w-0 flex-col">
      <span class="truncate leading-[1.3] font-semibold" :title="piece.title">
        {{ piece.title }}
      </span>
      <span class="truncate text-[13px] text-muted-foreground">
        {{ PLATFORM_LABEL[piece.platform] }} · {{ piece.source }} ·
        {{ formatUtcDay(piece.published_at) }}
      </span>
    </span>
    <span class="flex min-w-0 items-center gap-1.5 text-[13.5px] text-ink-soft">
      <StageDot :lifecycle="piece.opportunity.lifecycle" />
      <span class="truncate" :title="piece.opportunity.topic">{{ piece.opportunity.topic }}</span>
    </span>
    <!-- Sin ratio no hay cifra: se dice por qué, nunca 0 (CLAUDE.md §2.3). -->
    <span v-if="piece.outlier_ratio == null" class="text-right text-[13px] text-muted-foreground">
      {{ missingRatioLabel(piece) }}
    </span>
    <span
      v-else
      class="justify-self-end rounded-lg px-2 py-0.5 text-[13px] font-semibold"
      :class="
        piece.is_outlier ? 'bg-signal text-signal-foreground' : 'bg-neutral-action text-ink-read'
      "
    >
      {{ formatRatio(piece.outlier_ratio) }}
    </span>
  </button>
</template>
