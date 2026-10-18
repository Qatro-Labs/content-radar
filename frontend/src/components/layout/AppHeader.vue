<script setup lang="ts">
import { ChartLine, PenLine, Radar } from '@lucide/vue'
import { useRoute } from 'vue-router'

import { USING_FIXTURES } from '@/api/opportunities'
import { AGENT_ANCHOR } from '@/lib/agentTargets'
import { RouteName } from '@/router'

import DataStatus from './DataStatus.vue'
import PeriodControl from './PeriodControl.vue'
import SearchButton from './SearchButton.vue'

const route = useRoute()

// Una vista de la nav puede abarcar varias rutas: Explorar incluye el expediente de cada tema.
const views = [
  {
    name: RouteName.Discover,
    label: 'Radar',
    icon: Radar,
    routes: [RouteName.Discover],
    agentTarget: AGENT_ANCHOR.navRadar,
  },
  {
    name: RouteName.Explore,
    label: 'Explorar',
    icon: ChartLine,
    routes: [RouteName.Explore, RouteName.Dossier],
    agentTarget: AGENT_ANCHOR.navExplore,
  },
  // Rad no actúa en Crear: no necesita ancla.
  {
    name: RouteName.Create,
    label: 'Crear',
    icon: PenLine,
    routes: [RouteName.Create],
    agentTarget: undefined,
  },
] as const

function isCurrent(routes: readonly string[]): boolean {
  return typeof route.name === 'string' && routes.includes(route.name)
}
</script>

<template>
  <header class="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
    <div class="flex flex-wrap items-center gap-x-6 gap-y-2">
      <RouterLink
        :to="{ name: RouteName.Discover }"
        class="flex h-11 items-center gap-2 rounded-[10px] font-display text-xl font-bold tracking-[-0.03em]"
      >
        <span class="size-3.5 rounded-[4px] bg-signal" aria-hidden="true" />
        30X Signal
      </RouterLink>

      <nav aria-label="Vistas" class="flex flex-wrap items-center gap-1">
        <RouterLink
          v-for="view in views"
          :key="view.name"
          :to="{ name: view.name }"
          :data-agent="view.agentTarget"
          :aria-current="isCurrent(view.routes) ? 'page' : undefined"
          class="flex h-11 items-center gap-2 rounded-[10px] px-3.5 text-sm font-medium text-ink-soft transition-colors duration-150 ease-out hover:text-foreground aria-[current=page]:bg-card aria-[current=page]:font-semibold aria-[current=page]:text-foreground"
        >
          <component :is="view.icon" class="size-4 shrink-0" :stroke-width="2" aria-hidden="true" />
          {{ view.label }}
        </RouterLink>
      </nav>

      <SearchButton />
    </div>

    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <DataStatus />
      <PeriodControl v-if="route.name === RouteName.Discover" />
      <span
        v-if="USING_FIXTURES"
        class="rounded-full bg-sample px-3 py-1.5 text-[13px] font-medium text-notice-foreground"
      >
        Datos de ejemplo
      </span>
    </div>
  </header>
</template>
