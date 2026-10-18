<script setup lang="ts">
import { useIntervalFn, usePreferredReducedMotion } from '@vueuse/core'
import { computed, onMounted, ref, useTemplateRef, watch, watchEffect } from 'vue'

import RadMark, { type RadMarkState } from '@/components/agent/RadMark.vue'
import { CARD_CLASS } from '@/components/dossier/dossierClasses'
import {
  ABSORB_STAGGER_MS,
  citationSources,
  GENERATION_TITLE,
  GenerationStage,
  type GenerationTimeline,
  generationTimelineAt,
  isSameTimeline,
  pieceStatus,
  TYPICAL_WAIT_LABEL,
} from '@/lib/briefStages'
import { type BriefOptions, briefSentence } from '@/lib/briefView'
import { countLabel } from '@/lib/evidenceFormat'
import type { components } from '@/types/api'

import BriefGeneratingDraft, { type CitationView } from './BriefGeneratingDraft.vue'
import BriefGeneratingPiece from './BriefGeneratingPiece.vue'

interface Point {
  x: number
  y: number
}

const { pieces, pieceCount, options, done } = defineProps<{
  // Las piezas destacadas (featuredPieces), que Rad lee una a una.
  pieces: components['schemas']['Evidence'][]
  // Todas las piezas del tema; `null` si no se sabe.
  pieceCount: number | null
  options: BriefOptions
  // La API respondió con el brief.
  done: boolean
}>()

// Tras el cierre: quien la monta enseña el brief.
const emit = defineEmits<{ finished: [] }>()

// Artboard C1: Rad grande y centrado, protagonista de la espera; las piezas vuelan hasta él.
const RAD_SIZE_PX = 96
// Las etapas duran segundos y lo que pasa dentro de cada una lo anima CSS: basta con mirar el
// reloj diez veces por segundo.
const CLOCK_TICK_MS = 100
const WORKING_STAGES: readonly GenerationStage[] = [GenerationStage.Draft, GenerationStage.Check]

const motionPreference = usePreferredReducedMotion()
const isReduced = computed(() => motionPreference.value === 'reduce')

const startedAt = Date.now()
const elapsedMs = ref(0)
const clock = useIntervalFn(() => {
  elapsedMs.value = Date.now() - startedAt
}, CLOCK_TICK_MS)
const doneAtMs = ref<number | null>(null)
watch(
  () => done,
  (isDone) => {
    if (isDone && doneAtMs.value === null) doneAtMs.value = elapsedMs.value
  },
  { immediate: true },
)

const citations = computed(() => citationSources(pieces))
// El reloj late cada 100 ms, pero la vista solo cambia en los bordes de cada etapa: mientras nada
// cambie se reutiliza la línea de tiempo anterior, para no repintar en cada tic.
const timeline = computed<GenerationTimeline>((previous) => {
  const next = generationTimelineAt({
    elapsedMs: elapsedMs.value,
    pieceCount: pieces.length,
    citationCount: citations.value.length,
    doneAtMs: doneAtMs.value,
  })
  return previous && isSameTimeline(previous, next) ? previous : next
})

let hasFinished = false
// Con movimiento reducido no hay cierre que ver: el brief sale en cuanto responde la API.
watchEffect(() => {
  if (hasFinished || doneAtMs.value === null) return
  const canClose = isReduced.value || timeline.value.isFinished
  if (!canClose) return
  hasFinished = true
  clock.pause()
  emit('finished')
})

// Leídas todas, Rad absorbe las piezas y el borrador ocupa su sitio.
const isAbsorbed = computed(() => timeline.value.stage !== GenerationStage.Read)
const subtitle = computed(() => `${briefSentence(options)} · ${TYPICAL_WAIT_LABEL}`)
const morePieces = computed(() => (pieceCount === null ? 0 : pieceCount - pieces.length))
const citationViews = computed<CitationView[]>(() => {
  const { stage, checkedCount } = timeline.value
  if (stage !== GenerationStage.Check && stage !== GenerationStage.Done) return []
  return citations.value.map((name, index) => ({ name, isChecked: index < checkedCount }))
})

// Rad mira la pieza que lee y, al redactar, el borrador. La tarjeta es su `data-agent-root`: la
// marca mide su mirada respecto a ella (Rad no vive en Crear, así que no choca con la presencia).
const card = useTemplateRef<HTMLElement>('card')
const lookAt = ref<Point | null>(null)

function centerInCard(element: Element | null): Point | null {
  if (!element || !card.value) return null
  const box = element.getBoundingClientRect()
  const origin = card.value.getBoundingClientRect()
  return { x: box.left - origin.left + box.width / 2, y: box.top - origin.top + box.height / 2 }
}

function gazeTarget(): Point | null {
  const { stage, readingIndex } = timeline.value
  if (isReduced.value || !card.value || stage === GenerationStage.Done) return null
  const selector =
    stage === GenerationStage.Read
      ? `[data-generating-piece="${readingIndex}"]`
      : '[data-generating-draft]'
  return centerInCard(card.value.querySelector(selector))
}

function updateGaze() {
  lookAt.value = gazeTarget()
}

// Bajo la cabecera del tema, en una pantalla de portátil las piezas y el borrador quedarían fuera de
// la vista. Se sube la tarjeta arriba al empezar.
const SCROLL_MARGIN_PX = 16

function bringIntoView() {
  const top = (card.value?.getBoundingClientRect().top ?? 0) + window.scrollY - SCROLL_MARGIN_PX
  window.scrollTo({ top, behavior: isReduced.value ? 'auto' : 'smooth' })
}

onMounted(() => {
  bringIntoView()
  updateGaze()
})
watch([() => timeline.value.stage, () => timeline.value.readingIndex, isReduced], updateGaze, {
  flush: 'post',
})

// Lee en reposo; al redactar se abre en radar y su haz gira sin parar hasta que responde la API; al
// cerrar vuelve a ser un ojo y parpadea una vez (DESIGN.md §4 y §7).
const mark = computed<RadMarkState>(() => {
  const isWorking = WORKING_STAGES.includes(timeline.value.stage)
  return {
    working: isWorking,
    scanKey: 0,
    sweeping: isWorking,
    blinkKey: timeline.value.hasBlinked ? 1 : 0,
    lookAt: lookAt.value,
  }
})
</script>

<template>
  <section
    ref="card"
    data-agent-root
    aria-busy="true"
    aria-label="Generando el brief"
    :class="[CARD_CLASS, 'flex-col items-center gap-7 py-8']"
  >
    <div class="flex flex-col items-center gap-3 text-center">
      <RadMark data-rad-mark :state="mark" :size="RAD_SIZE_PX" />
      <p
        role="status"
        aria-live="polite"
        class="pt-2 font-display text-[22px] leading-[1.15] font-semibold tracking-[-0.02em] sm:text-2xl"
      >
        {{ GENERATION_TITLE[timeline.stage] }}
      </p>
      <p class="text-sm text-muted-foreground">{{ subtitle }}</p>
    </div>

    <!-- Piezas y borrador comparten celda: las piezas se van hacia Rad y el borrador nace donde
         estaban. La celda reserva desde el principio el alto del borrador con sus citas (316 px):
         la tarjeta no salta y el scroll del principio ya la deja entera a la vista. -->
    <div class="grid min-h-[316px] w-full">
      <div
        v-if="pieces.length > 0"
        class="flex flex-col gap-2.5 self-center [grid-area:1/1]"
        :aria-hidden="isAbsorbed"
      >
        <ul class="grid gap-2.5 sm:grid-cols-3">
          <BriefGeneratingPiece
            v-for="(piece, index) in pieces"
            :key="piece.url"
            :data-generating-piece="index"
            :piece
            :status="pieceStatus(timeline, index)"
            :absorbed="isAbsorbed"
            :absorb-delay-ms="index * ABSORB_STAGGER_MS"
          />
        </ul>
        <p
          v-if="morePieces > 0"
          class="text-center text-[13px] text-label transition-opacity duration-300 ease-out"
          :class="{ 'opacity-0': isAbsorbed }"
        >
          y {{ countLabel(morePieces, 'pieza más', 'piezas más') }} del tema
        </p>
      </div>

      <BriefGeneratingDraft
        v-if="isAbsorbed"
        class="w-full max-w-[680px] self-start justify-self-center [grid-area:1/1]"
        :citations="citationViews"
      />
    </div>
  </section>
</template>
