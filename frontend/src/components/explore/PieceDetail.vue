<script setup lang="ts">
import { ChevronLeft } from '@lucide/vue'
import { computed } from 'vue'

import PerformanceBar from '@/components/evidence/PerformanceBar.vue'
import {
  formatMetrics,
  formatVelocity,
  PLATFORM_LABEL,
  ratioLabel,
  type RatioLabel,
} from '@/lib/evidenceFormat'
import type { Piece } from '@/lib/exploreView'
import { formatUtcDay } from '@/lib/format'
import { isDescending, topicStageStyle } from '@/lib/lifecycle'
import { NOT_AVAILABLE } from '@/lib/opportunityFormat'
import { RouteName } from '@/router'

import StageDot from './StageDot.vue'

const { piece } = defineProps<{ piece: Piece }>()

const emit = defineEmits<{ clear: [] }>()

const META_SEPARATOR = ' · '
// DESIGN.md §4: "Qué no sabemos" es obligatorio en todo detalle.
const LIMITATION =
  'Que una pieza rinda más que su referencia no explica por qué funcionó: es una señal para revisarla, no una causa.'

// Sin ratio no hay rótulo: PerformanceBar ya dice por qué falta (D10 del plan fe-dashboard-v2).
const RATIO_CAPTION: Record<RatioLabel, string> = {
  Outlier: 'rinde 3× o más que su canal',
  Destacada: 'rinde 2× o más que su canal',
}

const caption = computed(() => {
  const label = ratioLabel(piece)
  return label === null ? null : RATIO_CAPTION[label]
})

const meta = computed(() =>
  [
    PLATFORM_LABEL[piece.platform],
    piece.source,
    `publicada el ${formatUtcDay(piece.published_at)}`,
  ].join(META_SEPARATOR),
)

const tiles = computed(() => [
  { label: 'Métricas públicas', value: formatMetrics(piece.metrics) ?? NOT_AVAILABLE },
  { label: 'Velocidad', value: formatVelocity(piece.velocity) ?? NOT_AVAILABLE },
])

// DESIGN.md §4.
const BUTTON_CLASS =
  'flex min-h-[46px] flex-[1_1_140px] items-center justify-center rounded-xl px-4 font-semibold transition-[background-color,scale] duration-150 ease-out active:scale-[0.98]'
</script>

<template>
  <div class="flex flex-col gap-4">
    <button
      type="button"
      class="flex min-h-11 items-center gap-1.5 self-start rounded-[10px] bg-secondary pr-3 pl-2 text-sm font-semibold transition-[background-color,scale] duration-150 ease-out hover:bg-secondary-hover active:scale-[0.98]"
      @click="emit('clear')"
    >
      <ChevronLeft class="size-4 text-ink-soft" :stroke-width="2" aria-hidden="true" />
      Resumen
    </button>

    <div class="flex flex-col gap-1.5">
      <PerformanceBar :evidence="piece" />
      <p v-if="caption" class="text-sm text-label">{{ caption }}</p>
    </div>

    <div class="flex flex-col gap-1">
      <h2 class="font-display text-[22px] leading-[1.15] font-semibold tracking-[-0.02em]">
        {{ piece.title }}
      </h2>
      <p class="text-sm text-muted-foreground">{{ meta }}</p>
    </div>

    <div class="grid grid-cols-2 gap-2">
      <div
        v-for="tile in tiles"
        :key="tile.label"
        class="flex min-w-0 flex-col gap-0.5 rounded-tile bg-sunken px-3 py-2.5"
      >
        <span class="text-[13px] text-muted-foreground">{{ tile.label }}</span>
        <span class="text-[14.5px] font-semibold">{{ tile.value }}</span>
      </div>
    </div>

    <div class="flex flex-col gap-2 rounded-tile bg-sunken px-4 py-3.5">
      <span class="text-[13px] text-muted-foreground">Tema</span>
      <span class="flex items-center gap-2">
        <StageDot
          :lifecycle="piece.opportunity.lifecycle"
          :descending="isDescending(piece.opportunity)"
        />
        <span class="text-[15px] leading-[1.3] font-semibold">{{ piece.opportunity.topic }}</span>
      </span>
      <span class="text-[13.5px] text-label">
        {{ topicStageStyle(piece.opportunity).label }}
      </span>
    </div>

    <div class="flex flex-col gap-1.5 rounded-tile bg-notice px-4 py-3.5">
      <p class="text-sm font-semibold text-notice-foreground">Qué no sabemos</p>
      <p class="text-sm text-ink-soft">{{ LIMITATION }}</p>
    </div>

    <div class="flex flex-wrap gap-2">
      <a
        :href="piece.url"
        target="_blank"
        rel="noopener noreferrer"
        class="bg-secondary text-secondary-foreground hover:bg-secondary-hover"
        :class="BUTTON_CLASS"
      >
        Ver original ↗
      </a>
      <RouterLink
        :to="{ name: RouteName.Dossier, params: { id: piece.opportunity.id } }"
        class="bg-primary text-primary-foreground hover:bg-primary-hover"
        :class="BUTTON_CLASS"
      >
        Abrir el tema
      </RouterLink>
    </div>
  </div>
</template>
