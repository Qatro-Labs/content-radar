<script setup lang="ts">
import { computed } from 'vue'

import { PEEK_DIM_CLASS } from '@/lib/agentPeek'
import type { AgentTurnView, TurnStatus } from '@/lib/agentTypes'
import { leadingWords } from '@/lib/answerWords'

import AgentEnding from './AgentEnding.vue'
import AgentSteps from './AgentSteps.vue'

const { turn, collapsed } = defineProps<{ turn: AgentTurnView; collapsed: boolean }>()

const emit = defineEmits<{
  selectCited: [id: string]
  copyLink: []
  askFromAssistant: [question: string]
  peekCited: [id: string | null]
}>()

const FINISHED_STATUSES: readonly TurnStatus[] = ['done', 'stopped', 'failed']

// Con el cierre ya a la vista, la respuesta va entera aunque la cuenta de palabras se quede corta.
const shownAnswer = computed(() => {
  if (turn.answer === null) return ''
  if (collapsed || turn.showEnding) return turn.answer.text
  return leadingWords(turn.answer.text, turn.visibleWords)
})

const isFinished = computed(() => FINISHED_STATUSES.includes(turn.status))
</script>

<template>
  <article class="flex flex-col gap-3">
    <h2
      class="font-display text-[19px] leading-[1.2] font-semibold tracking-[-0.02em]"
      :class="PEEK_DIM_CLASS"
    >
      {{ turn.question }}
    </h2>

    <AgentSteps
      :steps="turn.steps"
      :summary="turn.summary"
      :collapsible="collapsed || isFinished"
      :class="PEEK_DIM_CLASS"
    />

    <p
      v-if="shownAnswer"
      class="max-w-[720px] text-base leading-[1.55] whitespace-pre-line text-ink-read"
      :class="PEEK_DIM_CLASS"
    >
      {{ shownAnswer }}
    </p>

    <!-- DESIGN.md §4: el error va inline, en el turno afectado. -->
    <p
      v-if="turn.failure"
      class="rounded-tile bg-notice px-4 py-3 text-[14.5px] text-notice-foreground"
      :class="PEEK_DIM_CLASS"
    >
      {{ turn.failure }}
    </p>

    <p
      v-if="turn.status === 'stopped'"
      class="text-sm text-muted-foreground"
      :class="PEEK_DIM_CLASS"
    >
      Detenido
    </p>

    <!-- Las palabras no se anuncian una a una: solo el cierre, cuando la respuesta ya está entera. -->
    <div v-if="!collapsed" aria-live="polite">
      <AgentEnding
        v-if="turn.showEnding && turn.answer"
        :answer="turn.answer"
        :question="turn.question"
        @select-cited="(id) => emit('selectCited', id)"
        @copy-link="emit('copyLink')"
        @ask-from-assistant="(question) => emit('askFromAssistant', question)"
        @peek-cited="(id) => emit('peekCited', id)"
      />
    </div>
  </article>
</template>
