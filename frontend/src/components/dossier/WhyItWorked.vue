<script setup lang="ts">
import { computed } from 'vue'

import InfoTip from '@/components/layout/InfoTip.vue'
import { HELP } from '@/lib/helpText'
import { hookRows, unclassifiedNote } from '@/lib/whyItWorked'
import type { components } from '@/types/api'

import { CARD_CLASS, CARD_TITLE_CLASS } from './dossierClasses'

const { hooks } = defineProps<{ hooks: components['schemas']['OutlierHooks'] }>()

const rows = computed(() => hookRows(hooks))
const note = computed(() => unclassifiedNote(hooks))
</script>

<template>
  <section aria-label="Por qué funcionó" :class="[CARD_CLASS, 'flex-col gap-4']">
    <div class="flex flex-col gap-0.5">
      <h2 :class="[CARD_TITLE_CLASS, 'flex items-center gap-1.5']">
        Por qué funcionó
        <InfoTip label="por qué funcionó" :text="HELP.whyItWorked" />
      </h2>
      <!-- CLAUDE.md §1: se presenta como hipótesis, nunca como causalidad. -->
      <span class="text-sm text-muted-foreground">
        El gancho del título en los outliers frente al resto del tema. Es una pista, no una causa.
      </span>
    </div>

    <ul class="flex flex-col gap-2">
      <li
        v-for="row in rows"
        :key="row.hook"
        class="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 rounded-tile bg-sunken px-4 py-3.5"
      >
        <div class="flex min-w-0 flex-col gap-0.5">
          <span class="text-[15px] font-semibold">{{ row.label }}</span>
          <span class="text-[13.5px] text-label">{{ row.outliers }} · {{ row.rest }}</span>
        </div>
        <div class="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <span class="text-sm text-ink-soft">{{ row.comparison }}</span>
          <span
            class="rounded-full px-2.5 py-1 text-[13px] leading-[1.4] font-semibold whitespace-nowrap"
            :class="row.observed ? 'bg-signal text-foreground' : 'bg-secondary text-label'"
          >
            {{ row.verdict }}
          </span>
        </div>
      </li>
    </ul>

    <p v-if="note" class="text-[13.5px] text-muted-foreground">{{ note }}</p>
  </section>
</template>
