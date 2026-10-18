<script setup lang="ts">
import { ChartLine, PenLine, Radar } from '@lucide/vue'
import { useRoute } from 'vue-router'

import { USING_FIXTURES } from '@/api/opportunities'
import { AGENT_ANCHOR } from '@/lib/agentTargets'
import { HELP } from '@/lib/helpText'
import { RouteName } from '@/router'

import AuthControl from './AuthControl.vue'
import DataStatus from './DataStatus.vue'
import HoverHint from './HoverHint.vue'
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
    help: HELP.navRadar,
  },
  {
    name: RouteName.Explore,
    label: 'Explorar',
    icon: ChartLine,
    routes: [RouteName.Explore, RouteName.Dossier],
    agentTarget: AGENT_ANCHOR.navExplore,
    help: HELP.navExplore,
  },
  // Rad no actúa en Crear: no necesita ancla.
  {
    name: RouteName.Create,
    label: 'Crear',
    icon: PenLine,
    routes: [RouteName.Create],
    agentTarget: undefined,
    help: HELP.navCreate,
  },
] as const

function isCurrent(routes: readonly string[]): boolean {
  return typeof route.name === 'string' && routes.includes(route.name)
}
</script>

<template>
  <!-- Una sola fila desde 768px, en el orden del DOM. Por debajo, el orden visual cambia: arriba
       el logo con la búsqueda y la cuenta a la derecha, y la nav ocupa sola la segunda fila. El
       estado de los datos solo cabe desde 1280px; por debajo se oculta. -->
  <header class="flex flex-wrap items-center gap-x-2 gap-y-3 md:flex-nowrap md:gap-x-6">
    <RouterLink
      :to="{ name: RouteName.Discover }"
      class="order-1 flex h-11 shrink-0 items-center gap-2 rounded-[10px] font-display text-xl font-bold tracking-[-0.03em] whitespace-nowrap md:order-none"
    >
      <span class="size-3.5 rounded-[4px] bg-signal" aria-hidden="true" />
      30X Signal
    </RouterLink>

    <nav
      aria-label="Vistas"
      class="order-4 flex w-full items-center gap-1 md:order-none md:w-auto md:shrink-0"
    >
      <HoverHint v-for="view in views" :key="view.name" :text="view.help">
        <RouterLink
          :to="{ name: view.name }"
          :data-agent="view.agentTarget"
          :aria-current="isCurrent(view.routes) ? 'page' : undefined"
          class="flex h-11 flex-1 items-center justify-center gap-2 rounded-[10px] px-3.5 text-sm font-medium whitespace-nowrap text-ink-soft transition-colors duration-150 ease-out hover:text-foreground aria-[current=page]:bg-card aria-[current=page]:font-semibold aria-[current=page]:text-foreground md:flex-none"
        >
          <component :is="view.icon" class="size-4 shrink-0" :stroke-width="2" aria-hidden="true" />
          {{ view.label }}
        </RouterLink>
      </HoverHint>
    </nav>

    <div class="order-2 ml-auto flex min-w-0 md:order-none md:ml-0 lg:flex-1">
      <SearchButton />
    </div>

    <div class="hidden shrink-0 items-center gap-x-4 xl:flex">
      <HoverHint :text="HELP.lastCollection"><DataStatus /></HoverHint>
      <HoverHint v-if="route.name === RouteName.Discover" :text="HELP.period">
        <span class="text-[13px] font-medium whitespace-nowrap text-ink-soft">Últimos 7 días</span>
      </HoverHint>
    </div>
    <span
      v-if="USING_FIXTURES"
      class="order-3 shrink-0 rounded-full bg-sample px-3 py-1.5 text-[13px] font-medium whitespace-nowrap text-notice-foreground md:order-none"
    >
      Datos de ejemplo
    </span>

    <AuthControl class="order-3 shrink-0 md:order-none md:ml-auto lg:ml-0" />
  </header>
</template>
