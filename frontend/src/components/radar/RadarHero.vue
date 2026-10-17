<script setup lang="ts">
import { computed } from 'vue'

import ViewHeader from '@/components/layout/ViewHeader.vue'
import { LIFECYCLE_STYLE } from '@/lib/lifecycle'
import type { RadarQuery } from '@/lib/radarQuery'
import { radarHeadline, radarSubline, type RadarView } from '@/lib/radarView'

const props = defineProps<{ view: RadarView; query: RadarQuery }>()

const counters = computed(() => [
  {
    key: 'accelerating',
    value: props.view.counts.accelerating,
    label: 'acelerando',
    dotVar: LIFECYCLE_STYLE.accelerating.cssVar.fill,
  },
  {
    key: 'emerging',
    value: props.view.counts.emerging,
    label: 'emergentes',
    dotVar: LIFECYCLE_STYLE.emerging.cssVar.fill,
  },
  { key: 'latamGap', value: props.view.counts.latamGap, label: 'con hueco en LATAM', dotVar: null },
])
</script>

<template>
  <section class="flex flex-wrap items-end justify-between gap-x-10 gap-y-5">
    <ViewHeader :title="radarHeadline(view, query)">
      {{ radarSubline(view, query) }}
    </ViewHeader>

    <ul class="flex flex-wrap gap-2" aria-label="Contadores">
      <li
        v-for="counter in counters"
        :key="counter.key"
        class="flex min-w-[150px] flex-col gap-0.5 rounded-2xl bg-card px-5 py-4"
      >
        <span class="font-display text-4xl leading-[1.05] font-semibold tracking-[-0.03em]">
          {{ counter.value }}
        </span>
        <span class="flex items-center gap-[7px] text-sm text-ink-soft">
          <span
            v-if="counter.dotVar"
            aria-hidden="true"
            class="size-2.5 rounded-[3px]"
            :style="{ backgroundColor: `var(${counter.dotVar})` }"
          />
          {{ counter.label }}
        </span>
      </li>
    </ul>
  </section>
</template>
