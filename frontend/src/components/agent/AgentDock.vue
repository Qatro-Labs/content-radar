<script setup lang="ts">
import { computed, nextTick, ref, useId, useTemplateRef, watch } from 'vue'

import { PEEK_DIM_CLASS, PEEK_DIM_COMPOSER_CLASS } from '@/lib/agentPeek'
import type { AgentStatus, AgentTurnView } from '@/lib/agentTypes'

import AgentComposer from './AgentComposer.vue'
import AgentFoldRow from './AgentFoldRow.vue'
import AgentMinimizeButton from './AgentMinimizeButton.vue'
import AgentTranscript from './AgentTranscript.vue'
import type { RadMarkState } from './RadMark.vue'

const { turns, status, suggestions, mark } = defineProps<{
  turns: AgentTurnView[]
  status: AgentStatus
  suggestions: string[]
  mark: RadMarkState
}>()

const emit = defineEmits<{
  ask: [question: string]
  stop: []
  newConversation: []
  selectCited: [id: string]
  copyLink: []
  askFromAssistant: [question: string]
  minimize: []
  peekCited: [id: string | null]
}>()

const transcriptId = useId()
const foldRow = useTemplateRef<InstanceType<typeof AgentFoldRow>>('foldRow')

// DESIGN.md §4, «Respuesta plegada»: la barra abierta tapaba justo lo que Rad acababa de señalar
// en la página. Solo se pliega una respuesta entera: tras un error o «Detener», el turno sigue a
// la vista para que se lea qué pasó.
const answeredTurn = computed(() => {
  const turn = turns.at(-1)
  if (status !== 'idle' || turn?.status !== 'done' || turn.answer === null) return null
  return turn
})
const isTranscriptOpen = ref(answeredTurn.value === null)

watch(answeredTurn, (turn) => {
  isTranscriptOpen.value = turn === null
})

const peekedId = ref<string | null>(null)

function peekCited(id: string | null) {
  peekedId.value = id
  emit('peekCited', id)
}

// Elegir un tema citado pliega la respuesta para que se vea el tema en la página. Si el turno
// falló después de responder, no hay fila con la que volver a abrirla: se queda abierta.
async function selectCited(id: string) {
  emit('selectCited', id)
  if (answeredTurn.value === null) return
  isTranscriptOpen.value = false
  await nextTick()
  foldRow.value?.focus()
}
</script>

<template>
  <!-- DESIGN.md §4 y §5: la barra flota sobre la página (fija, fuera del flujo: la conversación no
       deja un hueco vacío al final de la página) y por eso lleva la sombra flotante. Durante el
       vistazo se vuelve transparente, con un contorno para no perderla (sin cristal: §10).
       `data-agent-dock` marca dónde acaba el hueco visible para la presencia. -->
  <section
    data-agent-dock
    :data-peeking="peekedId === null ? undefined : ''"
    aria-label="Rad, el agente del Radar"
    class="group/dock fixed inset-x-4 bottom-4 z-40 mx-auto flex max-w-[840px] origin-bottom-right flex-col gap-3 rounded-card p-3 transition-[background-color,box-shadow] duration-150 ease-out motion-reduce:transition-none md:bottom-6"
    :class="
      peekedId === null
        ? 'bg-card shadow-float'
        : 'bg-transparent ring-1 ring-[rgb(18_20_24/0.16)] ring-inset'
    "
  >
    <!-- «Minimizar» siempre arriba a la izquierda, fuera del campo: dentro, pulsarlo contaba como
         entrar en la barra y las sugerencias asomaban justo antes de reducirla. -->
    <div class="flex min-h-8 items-center gap-2" :class="PEEK_DIM_CLASS">
      <AgentMinimizeButton @minimize="emit('minimize')" />
      <span class="text-[13px] font-semibold text-ink-soft">Rad</span>
      <button
        v-if="turns.length > 0"
        type="button"
        class="ml-auto flex min-h-10 items-center text-sm text-muted-foreground underline underline-offset-4 transition-colors duration-150 ease-out hover:text-foreground"
        @click="emit('newConversation')"
      >
        Nueva conversación
      </button>
    </div>

    <!-- Sin animación al plegar: la barra se encoge de golpe y la fila entra con su fundido. -->
    <Transition
      enter-from-class="translate-y-1 opacity-0"
      enter-active-class="transition duration-300 ease-out motion-reduce:transition-none"
    >
      <AgentTranscript
        v-if="turns.length > 0 && isTranscriptOpen"
        :id="transcriptId"
        :turns
        @select-cited="selectCited"
        @copy-link="emit('copyLink')"
        @ask-from-assistant="(question) => emit('askFromAssistant', question)"
        @peek-cited="peekCited"
      />
    </Transition>

    <AgentFoldRow
      v-if="answeredTurn?.answer"
      ref="foldRow"
      :question="answeredTurn.question"
      :cited-count="answeredTurn.answer.cited.length"
      :expanded="isTranscriptOpen"
      :controls="transcriptId"
      @toggle="isTranscriptOpen = !isTranscriptOpen"
    />

    <AgentComposer
      :busy="status !== 'idle'"
      :suggestions
      :mark
      :class="PEEK_DIM_COMPOSER_CLASS"
      @ask="(question) => emit('ask', question)"
      @stop="emit('stop')"
    />
  </section>
</template>
