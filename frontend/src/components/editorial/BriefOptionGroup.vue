<script setup lang="ts" generic="T extends string">
import { useId } from 'vue'

const { label, options, labels, modelValue } = defineProps<{
  label: string
  options: readonly T[]
  labels: Record<T, string>
  modelValue: T
}>()

// Emite también al pulsar la opción ya elegida (`defineModel` no lo haría): elegir cierra el hueco
// de la frase aunque la opción no cambie.
const emit = defineEmits<{ 'update:modelValue': [option: T] }>()

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
      class="flex flex-wrap gap-0.5 self-start rounded-xl bg-secondary p-1"
    >
      <button
        v-for="option in options"
        :key="option"
        type="button"
        :aria-pressed="modelValue === option"
        class="flex min-h-10 items-center justify-center rounded-[9px] px-3.5 text-sm font-medium text-ink-soft transition duration-150 ease-out hover:text-foreground active:scale-[0.98] aria-pressed:bg-card aria-pressed:font-semibold aria-pressed:text-foreground"
        @click="emit('update:modelValue', option)"
      >
        {{ labels[option] }}
      </button>
    </div>
  </div>
</template>
