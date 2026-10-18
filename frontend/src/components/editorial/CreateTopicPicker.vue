<script setup lang="ts">
import { Search } from '@lucide/vue'
import { computed } from 'vue'

import { useOpportunities } from '@/api/opportunities'
import {
  CARD_CLASS,
  CARD_TITLE_CLASS,
  SECONDARY_BUTTON_CLASS,
} from '@/components/dossier/dossierClasses'
import ViewHeader from '@/components/layout/ViewHeader.vue'
import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'
import { useSearchPalette } from '@/composables/useSearchPalette'
import { BRIEF_PARAM } from '@/lib/briefView'
import { countLabel } from '@/lib/evidenceFormat'
import { formatScore } from '@/lib/opportunityFormat'
import { DEFAULT_PERIOD } from '@/lib/radarQuery'
import { RouteName } from '@/router'

// Sin «Publicar ya» se ofrecen los primeros del ranking, y se dice así: nunca se rellena.
const FALLBACK_TOPICS = 3
const SKELETON_ROWS = 3

const listQuery = useOpportunities(DEFAULT_PERIOD)
const { open: paletteOpen } = useSearchPalette()

const items = computed(() => listQuery.data.value?.items ?? [])
const publishNow = computed(() =>
  items.value.filter((item) => item.recommendation === 'publish_now'),
)
const topics = computed(() =>
  publishNow.value.length > 0 ? publishNow.value : items.value.slice(0, FALLBACK_TOPICS),
)
const subline = computed(() => {
  if (publishNow.value.length > 0) {
    return `${countLabel(publishNow.value.length, 'tema está', 'temas están')} en «Publicar ya».`
  }
  return 'Ningún tema está en «Publicar ya» esta semana: estos son los primeros del ranking.'
})
</script>

<template>
  <div class="flex flex-col gap-5 pt-5">
    <!-- Ninguna vista pide «elige algo» (DESIGN.md §1): responde con los temas que conviene
         escribir ya. -->
    <ViewHeader title="¿De qué conviene escribir esta semana?">
      Un brief parte de una oportunidad del Radar y de su evidencia. Elige un tema para prepararlo.
    </ViewHeader>

    <section aria-label="Temas para escribir" :class="[CARD_CLASS, 'flex-col gap-4']">
      <div class="flex flex-col gap-1">
        <h2 :class="CARD_TITLE_CLASS">Para escribir ya</h2>
        <p v-if="listQuery.isSuccess.value" class="text-[15px] text-ink-soft">{{ subline }}</p>
      </div>

      <div v-if="listQuery.isPending.value" class="flex flex-col gap-2" aria-busy="true">
        <SkeletonBone v-for="row in SKELETON_ROWS" :key="row" class="h-14 rounded-tile" />
      </div>
      <div v-else-if="listQuery.isError.value" class="flex flex-col items-start gap-3">
        <p role="alert" class="text-[15px] text-ink-soft">No se pudieron cargar los temas.</p>
        <button type="button" :class="SECONDARY_BUTTON_CLASS" @click="listQuery.refetch()">
          Reintentar
        </button>
      </div>
      <p v-else-if="topics.length === 0" class="text-[15px] text-ink-soft">
        Todavía no hay temas analizados.
      </p>
      <ul v-else class="flex flex-col">
        <li v-for="topic in topics" :key="topic.id">
          <RouterLink
            :to="{ name: RouteName.Create, query: { [BRIEF_PARAM.opportunity]: topic.id } }"
            class="flex min-h-14 items-center gap-3.5 border-t border-table-line px-1 py-2 text-[15px] transition-colors duration-150 ease-out hover:bg-sunken"
          >
            <!-- Ancho fijo: los chips miden distinto y los títulos tienen que alinearse. -->
            <span class="flex w-[116px] shrink-0">
              <LifecycleChip :lifecycle="topic.lifecycle" />
            </span>
            <span class="min-w-0 grow font-medium">{{ topic.topic }}</span>
            <span
              class="shrink-0"
              :class="topic.opportunity_score == null ? 'text-muted-foreground' : 'font-semibold'"
            >
              {{ formatScore(topic.opportunity_score) }}
            </span>
          </RouterLink>
        </li>
      </ul>

      <button
        type="button"
        :class="[SECONDARY_BUTTON_CLASS, 'self-start']"
        @click="paletteOpen = true"
      >
        <Search class="size-4" aria-hidden="true" />
        Buscar otro tema
      </button>
    </section>
  </div>
</template>
