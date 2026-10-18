<script setup lang="ts">
import { ChevronDown } from '@lucide/vue'
import { computed, ref, useId } from 'vue'

import RadMark, { type RadMarkState } from './RadMark.vue'

const { busy, suggestions, mark } = defineProps<{
  busy: boolean
  suggestions: string[]
  mark: RadMarkState
}>()

const emit = defineEmits<{
  ask: [question: string]
  stop: []
  minimize: []
}>()

// El mismo límite que `MAX_QUESTION_CHARS` en backend/app/schemas/agent.py: más larga, la API
// responde 422.
const MAX_QUESTION_CHARS = 300

// DESIGN.md §4: primario y secundario de 46 px; «Preguntar» pasa a «Detener» mientras Rad trabaja.
const BUTTON_CLASS =
  'flex min-h-[46px] shrink-0 items-center justify-center rounded-xl px-4 font-semibold whitespace-nowrap transition-[background-color,scale] duration-150 ease-out active:scale-[0.98]'

const inputId = useId()
const hintId = useId()
const draft = ref('')
// Las sugerencias solo salen mientras la persona está en la barra: en reposo, la barra es una
// línea y no tapa la página.
const isFocused = ref(false)

const showSuggestions = computed(
  () => isFocused.value && !busy && draft.value === '' && suggestions.length > 0,
)

// Pasar el foco del campo a una sugerencia no cuenta como salir de la barra.
function leave(event: FocusEvent) {
  const next = event.relatedTarget
  const root = event.currentTarget
  if (next instanceof Node && root instanceof Node && root.contains(next)) return
  isFocused.value = false
}

// Mientras Rad trabaja, Enter no envía: el borrador se queda para la siguiente pregunta.
function submit() {
  const question = draft.value.trim()
  if (busy || question === '') return
  emit('ask', question)
  draft.value = ''
}
</script>

<template>
  <div class="flex flex-col gap-3" @focusin="isFocused = true" @focusout="leave">
    <ul v-if="showSuggestions" aria-label="Preguntas sugeridas" class="flex flex-wrap gap-2">
      <li v-for="suggestion in suggestions" :key="suggestion">
        <button
          type="button"
          class="min-h-10 rounded-[10px] bg-secondary px-3 py-2 text-left text-sm font-medium transition-[background-color,scale] duration-150 ease-out hover:bg-secondary-hover active:scale-[0.98]"
          @click="emit('ask', suggestion)"
        >
          {{ suggestion }}
        </button>
      </li>
    </ul>

    <form data-agent="composer" class="flex items-center gap-2" @submit.prevent="submit">
      <!-- `data-rad-mark`: de aquí sale y aquí vuelve el ojo al reducir y abrir la barra. -->
      <RadMark data-rad-mark :state="mark" />

      <label :for="inputId" class="sr-only">Pregunta para Rad</label>
      <input
        :id="inputId"
        v-model="draft"
        type="text"
        autocomplete="off"
        :maxlength="MAX_QUESTION_CHARS"
        :aria-describedby="hintId"
        placeholder="Pregúntale a Rad: ¿qué conviene publicar esta semana?"
        class="h-12 min-w-0 flex-1 rounded-xl bg-secondary px-4 text-[15px] text-foreground placeholder:text-muted-foreground"
      />

      <button
        v-if="busy"
        type="button"
        class="bg-secondary text-secondary-foreground hover:bg-secondary-hover"
        :class="BUTTON_CLASS"
        @click="emit('stop')"
      >
        Detener
      </button>
      <button
        v-else
        type="submit"
        class="bg-primary text-primary-foreground hover:bg-primary-hover"
        :class="BUTTON_CLASS"
      >
        Preguntar
      </button>
      <!-- La barra se reduce al ojo de Rad para no tapar la página; la conversación se conserva. -->
      <button
        type="button"
        aria-label="Reducir a Rad"
        title="Reducir"
        class="flex size-12 shrink-0 items-center justify-center rounded-xl text-ink-soft transition-[background-color,scale] duration-150 ease-out hover:bg-secondary active:scale-[0.96]"
        @click="emit('minimize')"
      >
        <ChevronDown class="size-5" :stroke-width="2" aria-hidden="true" />
      </button>
    </form>

    <p :id="hintId" class="sr-only">
      Rad lee las mismas oportunidades que ves y usa los mismos controles
    </p>
  </div>
</template>
