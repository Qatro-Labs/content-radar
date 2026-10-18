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
import { useMediaQuery } from '@vueuse/core'

import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'
import { useRadarQuery } from '@/composables/useRadarQuery'
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
// La misma forma que la vista cargada (DiscoverView): la pestaña de la URL decide si se dibuja el
// radar o la tabla, y en escritorio también cabe en la ventana, así que nada salta al cargar.
const { query } = useRadarQuery()
const fillsHeight = useMediaQuery('(min-width: 1024px)')
const SKELETON_ROWS = 8
// Sobre el lienzo el hueso pulsa hasta el mismo gris del fondo y desaparece: ahí va quieto y un
// punto más oscuro, como un contador sin cifra.
const ON_CANVAS = '!animate-none !bg-secondary-hover'
const SKELETON_LEGEND = 5
// Los tres contadores-filtro de la cabecera y los tres temas que «Esta semana» enseña como
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
    class="flex flex-col gap-4 lg:h-full"
    aria-busy="true"
    aria-label="Cargando oportunidades"
  >
    <div class="flex shrink-0 flex-wrap items-end justify-between gap-x-8 gap-y-4 pt-2">
      <div class="flex min-w-0 flex-[1_1_420px] flex-col gap-3">
        <SkeletonBone :class="[ON_CANVAS, 'h-14 w-full max-w-[520px] rounded-xl']" />
        <SkeletonBone :class="[ON_CANVAS, 'h-5 w-full max-w-[600px] rounded-full']" />
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

    <div
      class="flex flex-wrap items-start gap-4 lg:min-h-[440px] lg:flex-1 lg:flex-nowrap lg:items-stretch"
    >
      <div class="flex min-w-0 flex-[999_1_720px] flex-col gap-3 lg:min-h-0">
        <div :class="[CARD, 'gap-3 px-5 pt-5 pb-4 lg:min-h-0 lg:flex-1']">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <!-- Las dos pestañas, la de la URL en blanco como en RadarTabs. -->
            <div class="flex gap-1 rounded-[14px] bg-secondary p-1">
              <div
                v-for="tab in ['radar', 'ranking'] as const"
                :key="tab"
                class="flex h-14 w-[200px] items-center gap-3 rounded-[11px] px-4 sm:w-[220px]"
                :class="query.tab === tab ? 'bg-card' : ''"
              >
                <SkeletonBone class="size-5 shrink-0 rounded-md" />
                <span class="flex grow flex-col gap-1.5">
                  <SkeletonBone class="h-4 w-16 rounded-md" />
                  <SkeletonBone class="h-3 w-32 rounded-full" />
                </span>
              </div>
            </div>
            <SkeletonBone v-if="query.tab === 'ranking'" class="h-3.5 w-48 rounded-full" />
          </div>

          <template v-if="query.tab === 'radar'">
            <div class="flex flex-wrap gap-1.5">
              <SkeletonBone
                v-for="chip in SKELETON_LEGEND"
                :key="chip"
                class="h-6 w-24 rounded-full"
              />
            </div>
            <div class="flex flex-col pt-1 pb-[30px] pl-[30px] lg:min-h-0 lg:flex-1">
              <SkeletonBone
                class="min-h-[240px] max-w-full rounded-tile lg:flex-1"
                :style="fillsHeight ? undefined : { aspectRatio: PLOT_ASPECT }"
              />
            </div>
            <SkeletonBone class="h-3.5 w-80 max-w-full rounded-full" />
          </template>

          <template v-else>
            <div class="flex flex-col gap-1.5 overflow-hidden lg:min-h-0 lg:flex-1">
              <SkeletonBone class="mb-1 h-4 w-full rounded-full" />
              <SkeletonBone
                v-for="row in SKELETON_ROWS"
                :key="row"
                class="h-12 shrink-0 rounded-lg"
              />
            </div>
            <div class="flex shrink-0 items-center justify-between gap-3 pt-2">
              <SkeletonBone class="h-3.5 w-28 rounded-full" />
              <SkeletonBone class="h-9 w-72 rounded-[10px]" />
            </div>
          </template>
        </div>
        <SkeletonBone :class="[ON_CANVAS, 'h-3.5 w-2/3 shrink-0 rounded-full']" />
      </div>

      <div
        :class="[
          CARD,
          'flex-[1_1_360px] gap-[18px] p-[22px] lg:min-h-0 lg:self-stretch lg:overflow-hidden',
        ]"
      >
        <div class="flex flex-col gap-2">
          <SkeletonBone class="h-7 w-36 rounded-lg" />
          <SkeletonBone class="h-4 w-4/5 rounded-full" />
        </div>
        <SkeletonBone
          v-for="pick in SKELETON_PICKS"
          :key="pick"
          class="h-[68px] shrink-0 rounded-tile"
        />
        <SkeletonBone class="h-12 shrink-0 rounded-tile" />
        <SkeletonBone class="h-20 shrink-0 rounded-tile" />
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
