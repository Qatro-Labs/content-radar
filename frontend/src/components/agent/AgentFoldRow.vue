<script setup lang="ts">
import { ChevronDown, ChevronUp } from '@lucide/vue'
import { computed, useTemplateRef } from 'vue'

import { PEEK_DIM_CLASS } from '@/lib/agentPeek'
import { countLabel } from '@/lib/evidenceFormat'
import { TEXT_ENTER_CLASS } from '@/lib/motion'

const { question, citedCount, expanded, controls } = defineProps<{
  question: string
  citedCount: number
  expanded: boolean
  // Id de la transcripción que abre y cierra.
  controls: string
}>()

const emit = defineEmits<{ toggle: [] }>()

const citedText = computed(() =>
  citedCount > 0 ? `· ${countLabel(citedCount, 'tema citado', 'temas citados')}` : null,
)

// Al plegar la respuesta desde un chip, el chip desaparece: el foco pasa aquí para no perderse.
const toggleButton = useTemplateRef<HTMLButtonElement>('toggleButton')
defineExpose({ focus: () => toggleButton.value?.focus() })
</script>

<template>
  <!-- El vistazo atenúa el envoltorio: la entrada de la fila (`duration-300`) pisaría su fundido. -->
  <div :class="PEEK_DIM_CLASS">
    <div
      class="flex items-center gap-3 rounded-tile bg-sunken px-3 py-2.5"
      :class="TEXT_ENTER_CLASS"
    >
      <span
        aria-hidden="true"
        class="size-[9px] shrink-0 rounded-full border-[1.5px] border-(--lc-accelerating-stroke) bg-signal"
      />
      <p class="flex min-w-0 flex-1 items-baseline gap-1.5 text-sm">
        <span class="shrink-0 font-semibold">Rad respondió</span>
        <span class="min-w-0 truncate text-muted-foreground">{{ question }}</span>
        <span v-if="citedText" class="shrink-0 whitespace-nowrap text-muted-foreground">
          {{ citedText }}
        </span>
      </p>
      <button
        ref="toggleButton"
        type="button"
        :aria-expanded="expanded"
        :aria-controls="controls"
        class="flex h-9 shrink-0 items-center gap-1.5 rounded-[10px] bg-card px-3 text-sm font-semibold transition-[background-color,scale] duration-150 ease-out hover:bg-secondary-hover active:scale-[0.98]"
        @click="emit('toggle')"
      >
        {{ expanded ? 'Ocultar respuesta' : 'Ver respuesta' }}
        <ChevronDown
          v-if="expanded"
          class="size-4 text-ink-soft"
          :stroke-width="2"
          aria-hidden="true"
        />
        <ChevronUp v-else class="size-4 text-ink-soft" :stroke-width="2" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>
