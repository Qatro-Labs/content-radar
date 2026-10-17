<script setup lang="ts">
import { TEXT_ENTER_CLASS } from '@/lib/motion'
import type { RankedOpportunity } from '@/lib/radarView'

const { opportunity } = defineProps<{ opportunity: RankedOpportunity }>()
</script>

<template>
  <section
    aria-label="Por qué importa"
    class="flex min-w-0 flex-col gap-3.5 rounded-card bg-card px-6 py-[22px]"
  >
    <h2 class="font-display text-xl font-semibold tracking-[-0.02em]">Por qué importa</h2>

    <p
      :key="opportunity.id"
      class="max-w-[720px] text-lg leading-[1.55] text-ink-read"
      :class="TEXT_ENTER_CLASS"
    >
      {{ opportunity.why_it_matters }}
    </p>

    <div
      data-agent="limit"
      class="mt-auto flex flex-wrap gap-x-3 gap-y-1 rounded-tile bg-notice px-4 py-3.5"
    >
      <h3 class="text-sm font-semibold text-notice-foreground">Qué no sabemos</h3>
      <ul
        v-if="opportunity.limitations.length > 0"
        :key="opportunity.id"
        class="flex flex-[1_1_280px] flex-col gap-1 text-[14.5px] text-ink-soft"
        :class="TEXT_ENTER_CLASS"
      >
        <!-- Por índice: el LLM puede repetir una limitación y la clave dejaría de ser única. -->
        <li v-for="(limitation, index) in opportunity.limitations" :key="index">
          {{ limitation }}
        </li>
      </ul>
      <p
        v-else
        :key="opportunity.id"
        class="flex-[1_1_280px] text-[14.5px] text-ink-soft"
        :class="TEXT_ENTER_CLASS"
      >
        El análisis no registró limitaciones.
      </p>
    </div>
  </section>
</template>
