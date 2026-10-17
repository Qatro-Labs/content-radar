<script setup lang="ts">
import { computed, ref, useId } from 'vue'

const { busy, suggestions } = defineProps<{ busy: boolean; suggestions: string[] }>()

const emit = defineEmits<{
  ask: [question: string]
  stop: []
}>()

// El mismo límite que `MAX_QUESTION_CHARS` en backend/app/schemas/agent.py: más larga, la API
// responde 422.
const MAX_QUESTION_CHARS = 300

// DESIGN.md §4: primario y secundario de 46 px; «Preguntar» pasa a «Detener» mientras Rad trabaja.
const BUTTON_CLASS =
  'flex min-h-[46px] shrink-0 items-center justify-center rounded-xl px-4 font-semibold whitespace-nowrap transition-[background-color,scale] duration-150 ease-out active:scale-[0.98]'

const inputId = useId()
const draft = ref('')

const showSuggestions = computed(() => !busy && draft.value === '' && suggestions.length > 0)

// Mientras Rad trabaja, Enter no envía: el borrador se queda para la siguiente pregunta.
function submit() {
  const question = draft.value.trim()
  if (busy || question === '') return
  emit('ask', question)
  draft.value = ''
}
</script>

<template>
  <div class="flex flex-col gap-3">
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
      <!-- Marca provisional del artboard E; el paso C.2 del plan la sustituye por RadMark. -->
      <span
        aria-hidden="true"
        class="flex size-10 shrink-0 items-center justify-center rounded-[11px] bg-foreground"
      >
        <span class="size-3 rounded-full bg-signal" />
      </span>

      <label :for="inputId" class="sr-only">Pregunta para Rad</label>
      <input
        :id="inputId"
        v-model="draft"
        type="text"
        autocomplete="off"
        :maxlength="MAX_QUESTION_CHARS"
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
    </form>

    <p class="text-[13px] text-muted-foreground">
      Rad lee las mismas oportunidades que ves y usa los mismos controles
    </p>
  </div>
</template>
