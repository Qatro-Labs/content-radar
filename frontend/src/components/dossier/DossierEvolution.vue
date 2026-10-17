<script setup lang="ts">
import { computed } from 'vue'

import type { QueryState } from '@/api/opportunities'
import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'
import { splitTimeline, type TimelineBar } from '@/lib/dossierView'
import { LIFECYCLE_STYLE } from '@/lib/lifecycle'
import {
  formatAcceleration,
  formatDecimal,
  GROWTH_LABEL,
  isDeclining,
} from '@/lib/opportunityFormat'
import type { components } from '@/types/api'

import { CARD_CLASS, CARD_TITLE_CLASS } from './dossierClasses'

type Schemas = components['schemas']

const { opportunity, timeline } = defineProps<{
  opportunity: Schemas['Opportunity']
  timeline: QueryState<Schemas['OpportunityTimeline'] | null>
}>()

// La barra más alta de las seis mide 130 px; un periodo sin piezas es un trazo de 3 px, nunca una
// barra vacía que se lea como "sin dato" (DESIGN.md §8). Las barras crecen escalonadas, 50 ms.
const BAR_MAX_PX = 130
const EMPTY_BAR_PX = 3
const BAR_STAGGER_MS = 50
const SKELETON_BARS = 6

interface WindowBar extends TimelineBar {
  heightPx: number
  colorClass: string
  delayMs: number
}

interface WindowTile {
  label: string
  isCurrent: boolean
  bars: WindowBar[]
}

const windows = computed(() =>
  timeline.data ? splitTimeline(timeline.data, opportunity.last_updated) : null,
)

// DESIGN.md §8: ventana actual en Tinta y anterior en gris; un periodo sin piezas, en su trazo.
function barColorClass(count: number, isCurrent: boolean): string {
  if (count === 0) return 'bg-window-empty'
  return isCurrent ? 'bg-foreground' : 'bg-window-previous'
}

function toWindowBars(bars: TimelineBar[], isCurrent: boolean, firstIndex: number): WindowBar[] {
  const scaleMax = windows.value?.scaleMax ?? 1
  return bars.map((bar, index) => ({
    ...bar,
    heightPx: bar.count === 0 ? EMPTY_BAR_PX : Math.round((bar.count / scaleMax) * BAR_MAX_PX),
    colorClass: barColorClass(bar.count, isCurrent),
    delayMs: (firstIndex + index) * BAR_STAGGER_MS,
  }))
}

const tiles = computed<WindowTile[]>(() => {
  const split = windows.value
  if (split === null) return []
  return [
    { label: split.previousLabel, isCurrent: false, bars: toWindowBars(split.previous, false, 0) },
    {
      label: split.currentLabel,
      isCurrent: true,
      bars: toWindowBars(split.current, true, split.previous.length),
    },
  ]
})
</script>

<template>
  <section
    data-agent="dossier-evolution"
    aria-label="Evolución"
    :class="[CARD_CLASS, 'flex-wrap gap-x-8 gap-y-6']"
  >
    <div class="flex min-w-0 flex-[999_1_640px] flex-col gap-3">
      <div class="flex items-center gap-3">
        <h2 :class="CARD_TITLE_CLASS">Evolución</h2>
        <span
          class="rounded-full bg-neutral-action px-2.5 py-1 text-[13px] font-semibold text-ink-read"
        >
          {{ GROWTH_LABEL[opportunity.growth_status] }}
        </span>
      </div>

      <div v-if="timeline.isPending" class="flex h-[180px] items-end gap-2.5" aria-busy="true">
        <SkeletonBone
          v-for="bar in SKELETON_BARS"
          :key="bar"
          class="h-3/5 grow rounded-t-lg rounded-b-[3px]"
        />
      </div>

      <template v-else-if="windows">
        <div class="flex flex-wrap gap-2.5">
          <div
            v-for="tile in tiles"
            :key="tile.label"
            class="flex flex-[1_1_260px] flex-col gap-2 rounded-tile bg-plot px-4 pt-4 pb-2.5"
          >
            <span
              class="text-[13px] font-semibold"
              :class="tile.isCurrent ? 'text-foreground' : 'text-muted-foreground'"
            >
              {{ tile.label }}
            </span>
            <div class="flex h-[180px] items-end gap-2.5">
              <div
                v-for="bar in tile.bars"
                :key="bar.date"
                class="flex h-full flex-[1_1_0] flex-col items-center justify-end gap-1.5"
              >
                <span
                  class="text-sm font-semibold"
                  :class="tile.isCurrent ? 'text-foreground' : 'text-muted-foreground'"
                >
                  {{ bar.count }}
                </span>
                <span
                  class="evolution-bar block w-full max-w-[72px] origin-bottom rounded-t-lg rounded-b-[3px]"
                  :class="bar.colorClass"
                  :style="{ height: `${bar.heightPx}px`, animationDelay: `${bar.delayMs}ms` }"
                  aria-hidden="true"
                />
                <span
                  class="text-[13px]"
                  :class="tile.isCurrent ? 'text-ink-soft' : 'text-muted-foreground'"
                >
                  {{ bar.label }}
                </span>
              </div>
            </div>
          </div>
        </div>
        <p class="text-[13.5px] text-muted-foreground">
          Piezas nuevas del tema en periodos de 24 h que terminan a las {{ windows.cutoffTime }} UTC
          del día indicado.
        </p>
      </template>

      <p v-else class="text-[15px] text-ink-soft">Evolución no disponible.</p>
    </div>

    <div class="flex min-w-0 flex-[1_1_300px] flex-col justify-center gap-2.5">
      <!-- DESIGN.md §2: la aceleración negativa va en Negativo. -->
      <span
        class="font-display text-[44px] leading-none font-semibold tracking-[-0.04em] whitespace-nowrap"
        :class="{ 'text-destructive': isDeclining(opportunity.acceleration) }"
      >
        {{ formatAcceleration(opportunity.acceleration) }}
      </span>
      <span class="text-base text-ink-soft">
        frente a la ventana anterior, ajustado por el volumen de las fuentes.
      </span>
      <span class="text-[15px] text-ink-soft">
        {{ formatDecimal(opportunity.velocity) }} piezas nuevas al día en la ventana actual.
      </span>
      <span class="text-sm text-muted-foreground">
        Etapa «{{ LIFECYCLE_STYLE[opportunity.lifecycle].label }}»:
        {{ opportunity.lifecycle_reason }}
      </span>
    </div>
  </section>
</template>

<style scoped>
/* DESIGN.md §7 y D12: las barras crecen desde abajo con `transform`, sin animar la altura. */
.evolution-bar {
  animation: evolution-bar-grow 420ms var(--ease-out) backwards;
}

@media (prefers-reduced-motion: reduce) {
  .evolution-bar {
    animation: none;
  }
}

@keyframes evolution-bar-grow {
  from {
    transform: scaleY(0);
  }
}
</style>
