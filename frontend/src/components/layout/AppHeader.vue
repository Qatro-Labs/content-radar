<script setup lang="ts">
import { useRoute } from 'vue-router'

import { USING_FIXTURES } from '@/api/opportunities'
import { RouteName } from '@/router'

import DataStatus from './DataStatus.vue'
import PeriodControl from './PeriodControl.vue'

const route = useRoute()

const views = [
  { name: RouteName.Discover, label: 'Radar' },
  { name: RouteName.Explore, label: 'Explorar' },
  { name: RouteName.Create, label: 'Crear' },
] as const
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

      <nav aria-label="Vistas" class="flex items-center gap-1">
        <RouterLink
          v-for="view in views"
          :key="view.name"
          :to="{ name: view.name }"
          :aria-current="route.name === view.name ? 'page' : undefined"
          class="flex h-11 items-center rounded-[10px] px-4 text-sm font-medium text-ink-soft transition-colors duration-150 ease-out hover:text-foreground aria-[current=page]:bg-card aria-[current=page]:font-semibold aria-[current=page]:text-foreground"
        >
          {{ view.label }}
        </RouterLink>
      </nav>
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
