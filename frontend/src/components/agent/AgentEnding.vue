<script setup lang="ts">
import { ArrowUpRight } from '@lucide/vue'
import { onKeyStroke } from '@vueuse/core'
import { computed, onBeforeUnmount, ref, useId } from 'vue'

import StageDot from '@/components/explore/StageDot.vue'
import { AGENT_TIMING } from '@/lib/agentMotion'
import { PEEK_DIM_CLASS } from '@/lib/agentPeek'
import type { AnswerEvent } from '@/lib/agentTypes'
import { TEXT_ENTER_CLASS } from '@/lib/motion'
import { formatScore } from '@/lib/opportunityFormat'

const { answer, question } = defineProps<{ answer: AnswerEvent; question: string }>()

const emit = defineEmits<{
  selectCited: [id: string]
  copyLink: []
  askFromAssistant: [question: string]
  peekCited: [id: string | null]
}>()

type CopyFeedback = 'link' | 'question'

// El aviso dura lo justo para leerlo, como «Enlace copiado» en el expediente (D10 del plan
// fe-radar-agent).
const COPIED_FEEDBACK_MS = 2000
// Con el retardo del escalonado, cada bloque espera oculto en el primer fotograma de su entrada.
const ENDING_BLOCK_CLASS = `${TEXT_ENTER_CLASS} fill-mode-backwards`
const FEEDBACK_CLASS = 'text-[13px] text-muted-foreground'
const CHIP_CLASS =
  'flex min-h-10 max-w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-sm transition-[background-color,box-shadow,opacity,scale] duration-150 ease-out active:scale-[0.98] motion-reduce:transition-none'
const LINK_CLASS =
  'inline-flex min-h-10 items-center gap-1 text-sm font-medium text-ink-soft underline underline-offset-4 transition-colors duration-150 ease-out hover:text-foreground'

const citedTitleId = useId()
const feedback = ref<CopyFeedback | null>(null)
let feedbackTimer: ReturnType<typeof setTimeout> | undefined

function showFeedback(kind: CopyFeedback) {
  feedback.value = kind
  clearTimeout(feedbackTimer)
  feedbackTimer = setTimeout(() => {
    feedback.value = null
  }, COPIED_FEEDBACK_MS)
}

// DESIGN.md §4, «Vistazo»: pasar el cursor o el foco por un chip deja ver su tema en la página.
const peekedId = ref<string | null>(null)

function peek(id: string) {
  if (peekedId.value === id) return
  peekedId.value = id
  emit('peekCited', id)
}

function endPeek() {
  if (peekedId.value === null) return
  peekedId.value = null
  emit('peekCited', null)
}

// Con el ratón encima, el foco puede estar en otro sitio: Escape se escucha en toda la ventana.
onKeyStroke('Escape', () => endPeek())

// Al pulsar un chip la respuesta se pliega y los chips desaparecen sin `mouseleave` ni `blur`:
// sin esto, la página se quedaría resaltando el tema.
onBeforeUnmount(() => {
  clearTimeout(feedbackTimer)
  endPeek()
})

function selectCited(id: string) {
  endPeek()
  emit('selectCited', id)
}

// Durante el vistazo, los chips son lo único sólido de la barra transparente.
function chipClass(id: string) {
  if (peekedId.value === null) return 'bg-secondary hover:bg-secondary-hover'
  if (id === peekedId.value)
    return 'bg-card shadow-float outline-2 outline-offset-2 outline-foreground'
  return 'bg-card shadow-float opacity-55'
}

function copyLink() {
  emit('copyLink')
  showFeedback('link')
}

function askFromAssistant() {
  emit('askFromAssistant', question)
  showFeedback('question')
}

const hasCited = computed(() => answer.cited.length > 0)
// Sin «Citadas», el escalonado empieza en «Qué no sabemos».
const unknownsOrder = computed(() => (hasCited.value ? 1 : 0))

// DESIGN.md §7: «Citadas», «Qué no sabemos» y los enlaces entran escalonados.
function staggerStyle(order: number) {
  return { animationDelay: `${order * AGENT_TIMING.endingStaggerMs}ms` }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <section
      v-if="hasCited"
      :aria-labelledby="citedTitleId"
      class="flex flex-col gap-2"
      :class="ENDING_BLOCK_CLASS"
      :style="staggerStyle(0)"
    >
      <h3 :id="citedTitleId" class="text-sm font-semibold text-label" :class="PEEK_DIM_CLASS">
        Citadas
      </h3>
      <ul class="flex flex-wrap gap-2">
        <li v-for="cited in answer.cited" :key="cited.id" class="max-w-full">
          <button
            type="button"
            :class="[CHIP_CLASS, chipClass(cited.id)]"
            @mouseenter="peek(cited.id)"
            @mouseleave="endPeek"
            @focus="peek(cited.id)"
            @blur="endPeek"
            @click="selectCited(cited.id)"
          >
            <StageDot :lifecycle="cited.lifecycle" />
            <span class="min-w-0 font-medium">{{ cited.topic }}</span>
            <span class="whitespace-nowrap text-muted-foreground">
              Oportunidad {{ formatScore(cited.opportunity_score) }}
            </span>
          </button>
        </li>
      </ul>
    </section>

    <!-- El vistazo atenúa este envoltorio y no cada bloque: la entrada escalonada de los bloques
         (`duration-300`) pisaría su fundido de 150 ms. -->
    <div class="flex flex-col gap-4" :class="PEEK_DIM_CLASS">
      <!-- DESIGN.md §9: la respuesta del agente siempre termina con «Qué no sabemos». -->
      <section
        class="flex flex-col gap-1.5 rounded-tile bg-notice px-4 py-3.5"
        :class="ENDING_BLOCK_CLASS"
        :style="staggerStyle(unknownsOrder)"
      >
        <h3 class="text-[15px] font-semibold text-notice-foreground">Qué no sabemos</h3>
        <ul class="flex list-disc flex-col gap-1 pl-5 text-[14.5px] text-ink-soft">
          <!-- Por índice: el modelo puede repetir una limitación y la clave dejaría de ser única. -->
          <li v-for="(unknown, index) in answer.unknowns" :key="index">{{ unknown }}</li>
        </ul>
      </section>

      <div
        class="flex flex-wrap items-center gap-x-5"
        :class="ENDING_BLOCK_CLASS"
        :style="staggerStyle(unknownsOrder + 1)"
      >
        <span class="inline-flex items-center gap-2">
          <button type="button" :class="LINK_CLASS" @click="copyLink">
            Copiar enlace a esta vista
          </button>
          <span v-if="feedback === 'link'" :class="FEEDBACK_CLASS"> Enlace copiado </span>
        </span>
        <!-- D10: solo «un asistente» hasta que haya un cliente MCP probado (docs/mcp.md). -->
        <span class="inline-flex items-center gap-2">
          <button type="button" :class="LINK_CLASS" @click="askFromAssistant">
            Hacer esta pregunta desde un asistente (MCP)
            <ArrowUpRight class="size-4 shrink-0" aria-hidden="true" />
          </button>
          <span v-if="feedback === 'question'" :class="FEEDBACK_CLASS"> Pregunta copiada </span>
        </span>
      </div>
    </div>
  </div>
</template>
