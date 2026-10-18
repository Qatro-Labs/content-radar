<script setup lang="ts">
import { Check, X } from '@lucide/vue'
import { computed, ref, useId } from 'vue'

import type { AgentStepView, DoneEvent, StepKind, StepStatus } from '@/lib/agentTypes'
import { countLabel } from '@/lib/evidenceFormat'
import { TEXT_ENTER_CLASS } from '@/lib/motion'

const { steps, summary, collapsible } = defineProps<{
  steps: AgentStepView[]
  summary: DoneEvent | null
  collapsible: boolean
}>()

// DESIGN.md §4 y §9: «Datos» si el paso lee, «Vista» si mueve la página.
const KIND_CHIP: Record<StepKind, { label: string; class: string }> = {
  data: { label: 'Datos', class: 'bg-neutral-action text-ink-read' },
  view: { label: 'Vista', class: 'bg-signal text-signal-foreground' },
}

// El icono dice el estado; el lector de pantalla lo oye con este texto.
const STATUS_STYLE: Record<StepStatus, { label: string; textClass: string }> = {
  running: { label: 'En curso', textClass: 'font-semibold text-foreground' },
  done: { label: 'Hecho', textClass: 'text-ink-soft' },
  failed: { label: 'Falló', textClass: 'text-muted-foreground' },
}

const listId = useId()
const isOpen = ref(false)

const isFolded = computed(() => collapsible && summary !== null)

const summaryText = computed(() => {
  if (summary === null) return ''
  const total = countLabel(summary.steps, 'paso', 'pasos')
  return `Hizo ${total}: ${summary.data_steps} de datos y ${summary.view_steps} en la vista`
})
</script>

<template>
  <div v-if="steps.length > 0" class="flex flex-col gap-1.5">
    <button
      v-if="isFolded"
      type="button"
      :aria-expanded="isOpen"
      :aria-controls="listId"
      class="flex min-h-10 items-center self-start text-sm text-muted-foreground underline underline-offset-4 transition-colors duration-150 ease-out hover:text-foreground"
      @click="isOpen = !isOpen"
    >
      {{ summaryText }}
    </button>

    <ol v-show="!isFolded || isOpen" :id="listId" class="flex flex-col gap-2">
      <li
        v-for="step in steps"
        :key="step.id"
        class="flex items-center gap-2.5 text-sm"
        :class="TEXT_ENTER_CLASS"
      >
        <span
          role="img"
          :aria-label="STATUS_STYLE[step.status].label"
          class="flex size-4 shrink-0 items-center justify-center"
        >
          <Check v-if="step.status === 'done'" class="size-4 text-ink-soft" aria-hidden="true" />
          <X v-else-if="step.status === 'failed'" class="size-4 text-ink-soft" aria-hidden="true" />
          <span v-else class="size-[9px] rounded-full bg-foreground" />
        </span>
        <span class="min-w-0" :class="STATUS_STYLE[step.status].textClass">{{ step.label }}</span>
        <span
          class="shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold"
          :class="KIND_CHIP[step.kind].class"
        >
          {{ KIND_CHIP[step.kind].label }}
        </span>
      </li>
    </ol>
  </div>
</template>
