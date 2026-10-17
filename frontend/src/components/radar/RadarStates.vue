<script lang="ts">
// Lo que ocupa el sitio del Radar mientras no hay oportunidades que pintar (D12 del plan
// fe-radar-view).
export const RadarPlaceholder = {
  Loading: 'loading',
  Error: 'error',
  NotAnalyzed: 'not-analyzed',
  Empty: 'empty',
} as const
export type RadarPlaceholder = (typeof RadarPlaceholder)[keyof typeof RadarPlaceholder]
</script>

<script setup lang="ts">
import { RADAR_ASPECT } from '@/lib/radarChart'

const { state } = defineProps<{ state: RadarPlaceholder }>()

const emit = defineEmits<{ retry: [] }>()

const EMPTY_MESSAGE: Partial<Record<RadarPlaceholder, string>> = {
  [RadarPlaceholder.NotAnalyzed]: 'Todavía no hay análisis: el job analyze no ha corrido.',
  [RadarPlaceholder.Empty]: 'El último análisis no encontró temas con datos suficientes.',
}
const ERROR_MESSAGE = 'No se pudieron cargar las oportunidades.'

const PLOT_ASPECT = `${RADAR_ASPECT.width} / ${RADAR_ASPECT.height}`
const CARD = 'flex min-w-0 flex-col rounded-card bg-card'
const CARD_TITLE = 'font-display text-[22px] leading-tight font-semibold tracking-[-0.02em]'
const BONE = 'radar-bone block'
// Cinco filas dan la forma de la tabla sin alargar la página mientras carga.
const SKELETON_ROWS = 5
const SKELETON_COUNTERS = 3
const SKELETON_TILES = 3
const SKELETON_BARS = 3
// Hover del botón secundario (#E8EAED, DESIGN.md §4): no tiene token en main.css.
const RETRY_BUTTON =
  'min-h-11 rounded-xl px-4 text-sm font-semibold transition-[background-color,scale] duration-150 ease-out hover:bg-[#e8eaed] active:scale-[0.98]'
// Sobre el fondo del gráfico el secundario va en blanco, como "Restablecer vista" sobre el
// lienzo (DESIGN.md §4): el gris de siempre casi no se distingue de ese fondo.
const RETRY_ON_PLOT = 'bg-card'
const RETRY_ON_CARD = 'bg-secondary'
</script>

<template>
  <div
    v-if="state === RadarPlaceholder.Loading"
    class="flex flex-col gap-4"
    aria-busy="true"
    aria-label="Cargando oportunidades"
  >
    <div class="flex flex-wrap items-end justify-between gap-x-10 gap-y-5 pt-5 pb-1">
      <div class="flex w-full max-w-[600px] flex-col gap-3">
        <span :class="[BONE, 'h-14 w-4/5 rounded-xl']" />
        <span :class="[BONE, 'h-5 w-full rounded-full']" />
      </div>
      <div class="flex flex-wrap gap-2">
        <div
          v-for="counter in SKELETON_COUNTERS"
          :key="counter"
          class="flex h-[86px] w-[150px] flex-col justify-center gap-2.5 rounded-2xl bg-card px-5"
        >
          <span :class="[BONE, 'h-8 w-12 rounded-lg']" />
          <span :class="[BONE, 'h-3.5 w-24 rounded-full']" />
        </div>
      </div>
    </div>

    <div class="flex flex-wrap gap-3">
      <span :class="[BONE, 'h-11 w-[580px] max-w-full rounded-xl']" />
      <span :class="[BONE, 'h-11 w-[150px] rounded-xl']" />
    </div>

    <div class="flex flex-wrap gap-4">
      <div :class="[CARD, 'flex-[999_1_680px] gap-3.5 px-6 pt-5 pb-[22px]']">
        <span :class="[BONE, 'h-7 w-24 rounded-lg']" />
        <div class="pt-1 pb-[30px] pl-[30px]">
          <span
            :class="[BONE, 'min-h-[300px] max-w-full rounded-tile']"
            :style="{ aspectRatio: PLOT_ASPECT }"
          />
        </div>
      </div>
      <div :class="[CARD, 'flex-[1_1_380px] gap-5 p-6']">
        <div class="flex flex-col gap-2.5">
          <span :class="[BONE, 'h-7 w-28 rounded-full']" />
          <span :class="[BONE, 'h-8 w-full rounded-lg']" />
          <span :class="[BONE, 'h-4 w-3/4 rounded-full']" />
        </div>
        <div class="flex items-center gap-5">
          <span :class="[BONE, 'size-28 shrink-0 rounded-full']" />
          <div class="flex grow flex-col gap-2">
            <span :class="[BONE, 'h-4 w-3/4 rounded-full']" />
            <span :class="[BONE, 'h-9 w-28 rounded-[10px]']" />
          </div>
        </div>
        <div class="grid grid-cols-3 gap-2">
          <span
            v-for="tile in SKELETON_TILES"
            :key="tile"
            :class="[BONE, 'h-[72px] rounded-tile']"
          />
        </div>
        <div class="flex flex-col gap-4">
          <span v-for="bar in SKELETON_BARS" :key="bar" :class="[BONE, 'h-2 rounded-full']" />
        </div>
        <div class="mt-auto flex gap-2">
          <span :class="[BONE, 'h-[46px] grow rounded-xl']" />
          <span :class="[BONE, 'h-[46px] grow rounded-xl']" />
        </div>
      </div>
    </div>

    <div class="flex flex-wrap gap-4">
      <div :class="[CARD, 'flex-[1_1_360px] gap-4 px-6 py-[22px]']">
        <span :class="[BONE, 'h-6 w-44 rounded-lg']" />
        <span :class="[BONE, 'h-3 rounded-full']" />
        <span :class="[BONE, 'h-10 w-4/5 rounded-lg']" />
        <span :class="[BONE, 'h-4 w-full rounded-full']" />
      </div>
      <div :class="[CARD, 'flex-[2_1_520px] gap-3.5 px-6 py-[22px]']">
        <span :class="[BONE, 'h-6 w-40 rounded-lg']" />
        <span :class="[BONE, 'h-5 w-full rounded-full']" />
        <span :class="[BONE, 'h-5 w-2/3 rounded-full']" />
        <span :class="[BONE, 'mt-auto h-12 rounded-tile']" />
      </div>
    </div>

    <div :class="[CARD, 'gap-1.5 px-5 pt-5 pb-3']">
      <span :class="[BONE, 'mx-1 mb-3 h-7 w-28 rounded-lg']" />
      <span v-for="row in SKELETON_ROWS" :key="row" :class="[BONE, 'h-14 rounded-lg']" />
    </div>
  </div>

  <div v-else-if="state === RadarPlaceholder.Error" class="flex flex-col gap-4">
    <section aria-label="Radar de oportunidades" :class="[CARD, 'gap-3.5 px-6 pt-5 pb-[22px]']">
      <h2 :class="CARD_TITLE">Radar</h2>
      <div
        class="flex min-h-[300px] flex-col items-center justify-center gap-4 rounded-tile bg-plot p-6 text-center"
      >
        <p role="alert" class="text-[15px] text-ink-soft">{{ ERROR_MESSAGE }}</p>
        <button type="button" :class="[RETRY_BUTTON, RETRY_ON_PLOT]" @click="emit('retry')">
          Reintentar
        </button>
      </div>
    </section>
    <section aria-label="Ranking" :class="[CARD, 'gap-1.5 px-5 pt-5 pb-3']">
      <h2 :class="[CARD_TITLE, 'px-1']">Ranking</h2>
      <div class="flex flex-wrap items-center gap-x-4 gap-y-3 px-1 py-6">
        <p class="text-[15px] text-ink-soft">{{ ERROR_MESSAGE }}</p>
        <button type="button" :class="[RETRY_BUTTON, RETRY_ON_CARD]" @click="emit('retry')">
          Reintentar
        </button>
      </div>
    </section>
  </div>

  <section v-else aria-label="Radar de oportunidades" :class="[CARD, 'gap-3 p-6']">
    <h2 :class="CARD_TITLE">Radar</h2>
    <p class="text-[17px] leading-[1.55] text-ink-soft">{{ EMPTY_MESSAGE[state] }}</p>
  </section>
</template>

<style scoped>
/* DESIGN.md §4: los skeletons van de Pista a Lienzo en 1,6 s, sin spinners. Con movimiento
   reducido se quedan quietos (§7). */
.radar-bone {
  background-color: var(--track);
  animation: radar-bone 1.6s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  .radar-bone {
    animation: none;
  }
}

@keyframes radar-bone {
  50% {
    background-color: var(--background);
  }
}
</style>
