<script setup lang="ts" generic="T extends string">
import { useId } from 'vue'

const { label, options, labels } = defineProps<{
  label: string
  options: readonly T[]
  labels: Record<T, string>
}>()

const selected = defineModel<T>({ required: true })

const labelId = useId()
</script>

<template>
  <!-- Opciones cerradas, nunca texto libre: ningún texto de la persona llega al LLM (CLAUDE.md
       §2.6). Segmented control como el del periodo, con la pista dentro de la tarjeta. -->
  <div class="flex flex-col gap-2">
    <span :id="labelId" class="text-sm font-semibold text-label">{{ label }}</span>
    <div
      role="group"
      :aria-labelledby="labelId"
      class="flex flex-wrap gap-0.5 rounded-xl bg-secondary p-1"
    >
      <button
        v-for="option in options"
        :key="option"
        type="button"
        :aria-pressed="selected === option"
        class="flex min-h-10 grow items-center justify-center rounded-[9px] px-3 text-sm font-medium text-ink-soft transition duration-150 ease-out hover:text-foreground active:scale-[0.98] aria-pressed:bg-card aria-pressed:font-semibold aria-pressed:text-foreground"
        @click="selected = option"
      >
        {{ labels[option] }}
      </button>
    </div>
  </div>
</template>
