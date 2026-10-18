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
import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'
import { PLOT_ASPECT } from '@/lib/radarChart'

const { state } = defineProps<{ state: RadarPlaceholder }>()

const emit = defineEmits<{ retry: [] }>()

const EMPTY_MESSAGE: Partial<Record<RadarPlaceholder, string>> = {
  [RadarPlaceholder.NotAnalyzed]: 'Todavía no hay análisis: el job analyze no ha corrido.',
  [RadarPlaceholder.Empty]: 'El último análisis no encontró temas con datos suficientes.',
}
const ERROR_MESSAGE = 'No se pudieron cargar las oportunidades.'

const CARD = 'flex min-w-0 flex-col rounded-card bg-card'
const CARD_TITLE = 'font-display text-[22px] leading-tight font-semibold tracking-[-0.02em]'
// Cinco filas dan la forma de la tabla sin alargar la página mientras carga.
const SKELETON_ROWS = 5
// Los cuatro contadores-filtro de la cabecera y los tres temas que «Esta semana» enseña como
// mínimo (D9 del plan fe-dashboard-v2).
const SKELETON_COUNTERS = 3
const SKELETON_PICKS = 3
const RETRY_BUTTON =
  'min-h-11 rounded-xl px-4 text-sm font-semibold transition-[background-color,scale] duration-150 ease-out hover:bg-secondary-hover active:scale-[0.98]'
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
    <div class="flex flex-wrap items-end justify-between gap-x-8 gap-y-4 pt-5 pb-1">
      <div class="flex w-full max-w-[600px] flex-col gap-3">
        <SkeletonBone class="h-14 w-4/5 rounded-xl" />
        <SkeletonBone class="h-5 w-full rounded-full" />
      </div>
      <div class="flex flex-wrap gap-2">
        <div
          v-for="counter in SKELETON_COUNTERS"
          :key="counter"
          class="flex h-20 w-32 flex-col justify-center gap-2.5 rounded-2xl bg-card px-4"
        >
          <SkeletonBone class="h-8 w-12 rounded-lg" />
          <SkeletonBone class="h-3.5 w-20 rounded-full" />
        </div>
      </div>
    </div>

    <div class="flex flex-wrap items-start gap-4">
      <div class="flex min-w-0 flex-[999_1_720px] flex-col gap-4">
        <div :class="[CARD, 'gap-3.5 px-6 pt-5 pb-[22px]']">
          <SkeletonBone class="h-7 w-24 rounded-lg" />
          <div class="pt-1 pb-[30px] pl-[30px]">
            <SkeletonBone
              class="min-h-[300px] max-w-full rounded-tile"
              :style="{ aspectRatio: PLOT_ASPECT }"
            />
          </div>
        </div>
        <div :class="[CARD, 'gap-1.5 px-5 pt-5 pb-3']">
          <SkeletonBone class="mx-1 mb-3 h-7 w-28 rounded-lg" />
          <SkeletonBone v-for="row in SKELETON_ROWS" :key="row" class="h-14 rounded-lg" />
        </div>
      </div>

      <div :class="[CARD, 'flex-[1_1_360px] gap-[18px] p-[22px]']">
        <div class="flex flex-col gap-2">
          <SkeletonBone class="h-7 w-36 rounded-lg" />
          <SkeletonBone class="h-4 w-4/5 rounded-full" />
        </div>
        <SkeletonBone v-for="pick in SKELETON_PICKS" :key="pick" class="h-[68px] rounded-tile" />
        <SkeletonBone class="h-12 rounded-tile" />
        <SkeletonBone class="h-16 rounded-tile" />
      </div>
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
