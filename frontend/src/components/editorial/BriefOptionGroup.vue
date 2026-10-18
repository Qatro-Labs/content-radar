<script setup lang="ts" generic="T extends string">
import InfoTip from '@/components/layout/InfoTip.vue'
import { computed, useId } from 'vue'

const { label, options, labels, help } = defineProps<{
  label: string
  // Qué cambia esta opción en el brief: va en el tooltip del rótulo.
  help: string
  options: readonly T[]
  labels: Record<T, string>
}>()

const selected = defineModel<T>({ required: true })

const labelId = useId()

// Rejilla y no wrap libre: con wrap, la cuarta o la quinta opción quedaba sola en su fila. Cuatro
// opciones van de 2 en 2; tres o cinco, de 3 en 3.
const PAIRS = 4
const columnsClass = computed(() => (options.length === PAIRS ? 'grid-cols-2' : 'grid-cols-3'))
</script>

<template>
  <!-- Opciones cerradas, nunca texto libre: ningún texto de la persona llega al LLM (CLAUDE.md
       §2.6). Segmented control como el del periodo, con la pista dentro de la tarjeta. -->
  <div class="flex flex-col gap-2">
    <span class="flex items-center gap-1">
      <span :id="labelId" class="text-sm font-semibold text-label">{{ label }}</span>
      <InfoTip :label="label" :text="help" />
    </span>
    <div
      role="group"
      :aria-labelledby="labelId"
      class="grid gap-0.5 rounded-xl bg-secondary p-1"
      :class="columnsClass"
    >
      <button
        v-for="option in options"
        :key="option"
        type="button"
        :aria-pressed="selected === option"
        class="flex min-h-10 items-center justify-center rounded-[9px] px-2 text-sm font-medium text-ink-soft transition duration-150 ease-out hover:text-foreground active:scale-[0.98] aria-pressed:bg-card aria-pressed:font-semibold aria-pressed:text-foreground"
        @click="selected = option"
      >
        {{ labels[option] }}
      </button>
    </div>
  </div>
</template>
