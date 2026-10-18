<script setup lang="ts">
import { ArrowRight, Search } from '@lucide/vue'
import { computed, ref } from 'vue'

import { CARD_CLASS, CARD_TITLE_CLASS } from '@/components/dossier/dossierClasses'
import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import { BRIEF_PARAM } from '@/lib/briefView'
import { buildTopicList } from '@/lib/createPicker'
import { formatScore, SCORE_MAX } from '@/lib/opportunityFormat'
import { cn } from '@/lib/utils'
import { isDescending } from '@/lib/lifecycle'
import { RouteName } from '@/router'
import type { components } from '@/types/api'

const { topics, hasFeatured } = defineProps<{
  topics: components['schemas']['Opportunity'][]
  hasFeatured: boolean
}>()

const text = ref('')
const expanded = ref(false)

const view = computed(() =>
  buildTopicList({ topics, hasFeatured, text: text.value, expanded: expanded.value }),
)

// Cabecera y filas comparten anchos para que las columnas se lean como tabla. Por debajo de
// 640 px solo quedan el tema y la acción: la página nunca hace scroll horizontal (DESIGN.md §6).
// La etapa cabe entera: el chip más largo, «Sin tendencia clara», mide ~154 px.
const STAGE_COLUMN_CLASS = 'hidden w-[160px] shrink-0 sm:flex'
const RECOMMENDATION_COLUMN_CLASS = 'hidden w-[122px] shrink-0 sm:flex'
const SCORE_COLUMN_CLASS = 'hidden w-[112px] shrink-0 items-center gap-2.5 sm:flex'
const ACTION_COLUMN_CLASS = 'flex shrink-0 justify-end sm:w-32'
const ROW_GAP_CLASS = 'gap-2.5 sm:gap-4'
</script>

<template>
  <section :aria-label="view.title" :class="cn(CARD_CLASS, 'flex-col gap-4 pb-3')">
    <div class="flex flex-wrap items-end justify-between gap-3.5">
      <div class="flex flex-col gap-1">
        <h2 :class="CARD_TITLE_CLASS">{{ view.title }}</h2>
        <p class="text-[15px] text-ink-soft">{{ view.countLine }}</p>
      </div>
      <label
        class="flex h-[46px] min-w-0 flex-[1_1_260px] items-center gap-2.5 rounded-xl bg-secondary px-3.5 focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ring sm:flex-[0_1_360px]"
      >
        <Search
          class="size-4 shrink-0 text-muted-foreground"
          :stroke-width="2"
          aria-hidden="true"
        />
        <span class="sr-only">Buscar tema</span>
        <input
          v-model="text"
          type="search"
          placeholder="Buscar tema: agentes, coste, LATAM…"
          class="min-w-0 flex-1 bg-transparent text-[15px] text-foreground placeholder:text-muted-foreground focus-visible:outline-none"
        />
      </label>
    </div>

    <div class="flex flex-col">
      <!-- Solo visual: cada fila es un enlace, no una celda de tabla. -->
      <div
        aria-hidden="true"
        class="hidden items-center px-3 pb-2 text-[13px] font-medium text-muted-foreground sm:flex"
        :class="ROW_GAP_CLASS"
      >
        <span :class="STAGE_COLUMN_CLASS">Etapa</span>
        <span class="flex-1">Tema</span>
        <span :class="RECOMMENDATION_COLUMN_CLASS">Recomendación</span>
        <span :class="SCORE_COLUMN_CLASS">Oportunidad</span>
        <span :class="ACTION_COLUMN_CLASS" />
      </div>

      <ul class="flex flex-col">
        <li v-for="topic in view.rows" :key="topic.id">
          <RouterLink
            :to="{ name: RouteName.Create, query: { [BRIEF_PARAM.opportunity]: topic.id } }"
            class="group flex min-h-[60px] items-center border-t border-table-line px-3 py-2 transition-colors duration-150 ease-out hover:bg-sunken"
            :class="ROW_GAP_CLASS"
          >
            <span :class="STAGE_COLUMN_CLASS">
              <LifecycleChip :lifecycle="topic.lifecycle" :descending="isDescending(topic)" />
            </span>
            <span class="min-w-0 flex-1 text-[15px] leading-[1.35] font-medium">
              {{ topic.topic }}
            </span>
            <span :class="RECOMMENDATION_COLUMN_CLASS">
              <RecommendationChip :recommendation="topic.recommendation" size="sm" />
            </span>
            <span :class="SCORE_COLUMN_CLASS">
              <span class="sr-only">Oportunidad</span>
              <span
                v-if="topic.opportunity_score == null"
                class="text-sm whitespace-nowrap text-muted-foreground"
              >
                {{ formatScore(topic.opportunity_score) }}
              </span>
              <template v-else>
                <span class="h-1.5 w-14 overflow-hidden rounded-full bg-track" aria-hidden="true">
                  <span
                    class="topic-bar block h-full origin-left rounded-full bg-foreground"
                    :style="{ transform: `scaleX(${topic.opportunity_score / SCORE_MAX})` }"
                  />
                </span>
                <span class="text-[15px] font-semibold">
                  {{ formatScore(topic.opportunity_score) }}
                </span>
              </template>
            </span>
            <!-- Siempre visible, para que se vea que la fila es la acción; pasa a primario al
                 apuntarla o al llegar con el teclado. -->
            <span :class="ACTION_COLUMN_CLASS">
              <span
                class="inline-flex h-[38px] items-center gap-1.5 rounded-[10px] bg-secondary px-3.5 text-sm font-semibold whitespace-nowrap text-secondary-foreground transition-colors duration-150 ease-out group-hover:bg-primary group-hover:text-primary-foreground group-focus-visible:bg-primary group-focus-visible:text-primary-foreground"
              >
                Crear brief
                <ArrowRight class="size-3.5" :stroke-width="2.2" aria-hidden="true" />
              </span>
            </span>
          </RouterLink>
        </li>
      </ul>

      <p
        v-if="view.noMatches"
        class="border-t border-table-line px-3 py-[18px] text-[15px] text-ink-soft"
      >
        Ningún tema coincide con «{{ text.trim() }}».
      </p>
    </div>

    <button
      v-if="view.expandLabel"
      type="button"
      class="min-h-11 self-center px-3.5 text-sm font-semibold text-ink-soft underline underline-offset-4 transition-colors duration-150 ease-out hover:text-foreground"
      @click="expanded = true"
    >
      {{ view.expandLabel }}
    </button>
  </section>
</template>

<style scoped>
/* DESIGN.md §7: las barras de score crecen hasta su valor (420 ms) al entrar, con `scaleX`. */
.topic-bar {
  animation: topic-bar-grow 420ms var(--ease-out) backwards;
}

@media (prefers-reduced-motion: reduce) {
  .topic-bar {
    animation: none;
  }
}

@keyframes topic-bar-grow {
  from {
    transform: scaleX(0);
  }
}
</style>
