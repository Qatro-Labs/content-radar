<script setup lang="ts">
import { computed } from 'vue'

import { countLabel, formatCount } from '@/lib/evidenceFormat'
import type { SourceOutliers } from '@/lib/exploreView'
import { RouteName } from '@/router'
import type { components } from '@/types/api'

import StageDot from './StageDot.vue'

const { topTopics, topSources } = defineProps<{
  topTopics: components['schemas']['Opportunity'][]
  topSources: SourceOutliers[]
}>()

// HN no tiene canal: su referencia es el p90 de la búsqueda (CLAUDE.md §7).
const LIMITATION =
  'Que una pieza rinda 3× su referencia no explica por qué funcionó: es una señal para ' +
  'revisarla, no una causa. En Hacker News la referencia es el p90 de la búsqueda, no un canal.'

const hasOutliers = computed(() => topTopics.length > 0 || topSources.length > 0)

function outlierLabel(count: number): string {
  return countLabel(count, 'outlier', 'outliers')
}
</script>

<template>
  <div class="flex flex-col gap-[18px]">
    <div class="flex flex-col gap-1">
      <h2 class="font-display text-2xl leading-tight font-semibold tracking-[-0.02em]">
        Dónde está funcionando
      </h2>
      <p class="text-sm text-muted-foreground">Temas y fuentes con más outliers.</p>
    </div>

    <p v-if="!hasOutliers" class="text-[15px] text-ink-soft">
      Todavía no hay outliers en las piezas servidas.
    </p>

    <div v-if="topTopics.length > 0" class="flex flex-col gap-2">
      <h3 class="text-sm font-semibold">Temas</h3>
      <ul class="flex flex-col gap-2">
        <li v-for="topic in topTopics" :key="topic.id">
          <RouterLink
            :to="{ name: RouteName.Dossier, params: { id: topic.id } }"
            class="flex min-h-12 items-center gap-2.5 rounded-xl bg-sunken px-3 py-1.5 transition-colors duration-150 ease-out hover:bg-track"
          >
            <StageDot :lifecycle="topic.lifecycle" />
            <span class="min-w-0 grow text-sm leading-[1.3] font-medium">{{ topic.topic }}</span>
            <span class="shrink-0 text-[13.5px] font-semibold">
              {{ outlierLabel(topic.outlier_count) }}
            </span>
          </RouterLink>
        </li>
      </ul>
    </div>

    <div v-if="topSources.length > 0" class="flex flex-col gap-2">
      <h3 class="text-sm font-semibold">Fuentes</h3>
      <ul class="flex flex-col gap-2">
        <li v-for="source in topSources" :key="source.source" class="flex items-center gap-2.5">
          <span class="w-[132px] shrink-0 truncate text-sm text-ink-soft" :title="source.source">
            {{ source.source }}
          </span>
          <span class="h-1.5 grow overflow-hidden rounded-full bg-track" aria-hidden="true">
            <span
              class="block h-full origin-left rounded-full bg-foreground"
              :style="{ transform: `scaleX(${source.share})` }"
            />
          </span>
          <span class="min-w-5 text-right text-sm font-semibold">
            <span aria-hidden="true">{{ formatCount(source.count) }}</span>
            <span class="sr-only">{{ outlierLabel(source.count) }}</span>
          </span>
        </li>
      </ul>
    </div>

    <div class="flex flex-col gap-1.5 rounded-tile bg-notice px-4 py-3.5">
      <p class="text-sm font-semibold text-notice-foreground">Qué no sabemos</p>
      <p class="text-sm text-ink-soft">{{ LIMITATION }}</p>
    </div>
  </div>
</template>
