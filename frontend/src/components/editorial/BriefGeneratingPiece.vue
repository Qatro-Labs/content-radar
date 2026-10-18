<script setup lang="ts">
import { Check } from '@lucide/vue'
import { computed, ref, useTemplateRef, watch } from 'vue'

import { AGENT_ROOT_SELECTOR } from '@/lib/agentTargets'
import type { PieceStatus } from '@/lib/briefStages'
import { PLATFORM_LABEL, shortSourceName } from '@/lib/evidenceFormat'
import type { components } from '@/types/api'

interface Point {
  x: number
  y: number
}

const { piece, status } = defineProps<{
  piece: components['schemas']['Evidence']
  status: PieceStatus
}>()

// La marca de Rad de la tarjeta (BriefGenerating), destino de la fuente que vuela.
const RAD_MARK_SELECTOR = '[data-rad-mark]'
// El icono dice el estado; el lector de pantalla lo oye con este texto.
const STATUS_LABEL: Record<PieceStatus, string> = {
  pending: 'Por leer',
  reading: 'Leyendo',
  read: 'Leída',
}
// El check sale cuando el subrayado casi ha terminado de pasar.
const CHECK_POP_DELAY_MS = 600

const isStarted = computed(() => status !== 'pending')
const pill = useTemplateRef<HTMLElement>('pill')
const flight = ref<Point | null>(null)

function centerOf(rect: DOMRect): Point {
  return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 }
}

// FLIP: la píldora se mide donde nace (sobre el nombre de la fuente) y vuela hasta el centro de
// Rad con `transform`; las variables CSS llevan el desplazamiento a la animación.
function flightToRad(element: HTMLElement): Point | null {
  const mark = element.closest(AGENT_ROOT_SELECTOR)?.querySelector(RAD_MARK_SELECTOR)
  if (!mark) return null
  const from = centerOf(element.getBoundingClientRect())
  const to = centerOf(mark.getBoundingClientRect())
  return { x: to.x - from.x, y: to.y - from.y }
}

watch(pill, (element) => {
  if (element) flight.value = flightToRad(element)
})

const flightStyle = computed(() =>
  flight.value ? { '--fly-x': `${flight.value.x}px`, '--fly-y': `${flight.value.y}px` } : {},
)
</script>

<template>
  <div
    class="flex items-center gap-3.5 rounded-tile bg-sunken px-3.5 py-3 transition-transform duration-300 ease-out motion-reduce:transition-none"
    :class="{ '-translate-y-[5px]': status === 'reading' }"
  >
    <span class="flex min-w-0 grow flex-col gap-0.5">
      <span class="text-[13px] text-label">
        <span class="font-semibold text-ink-read">{{ PLATFORM_LABEL[piece.platform] }}</span>
        ·
        <span class="relative">
          {{ piece.source }}
          <!-- La fuente se despega como una píldora lima y vuela hasta Rad. -->
          <span
            v-if="isStarted"
            ref="pill"
            aria-hidden="true"
            class="brief-pill"
            :style="flightStyle"
          >
            {{ shortSourceName(piece.source) }}
          </span>
        </span>
      </span>
      <!-- El subrayado pasa por el título real: Rad no se inventa qué frase se lleva. Texto
           externo interpolado, nunca como HTML (CLAUDE.md §2.6). -->
      <span
        class="brief-highlight block max-w-full self-start truncate text-[15px] leading-[1.45] font-semibold"
        :class="{ 'is-marked': isStarted }"
      >
        {{ piece.title }}
      </span>
    </span>
    <span
      role="img"
      :aria-label="STATUS_LABEL[status]"
      class="relative flex size-[22px] shrink-0 rounded-full bg-track"
    >
      <span
        v-if="isStarted"
        class="brief-check absolute inset-0 flex items-center justify-center rounded-full bg-primary"
        :style="status === 'reading' ? { '--pop-delay': `${CHECK_POP_DELAY_MS}ms` } : {}"
      >
        <Check class="size-3 text-signal" :stroke-width="3.4" aria-hidden="true" />
      </span>
    </span>
  </div>
</template>

<style scoped>
/* Rotulador lima bajo el título (canvas de Crear, C1): una capa que crece con `scaleX`, solo
   `transform` (DESIGN.md §7). La lima va de relleno bajo la tinta (§2). */
.brief-highlight {
  position: relative;
  z-index: 0;
  padding-inline: 2px;
}

.brief-highlight::before {
  content: '';
  position: absolute;
  inset: 56% 0 0;
  z-index: -1;
  border-radius: 3px;
  background: var(--signal);
  opacity: 0.75;
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 650ms var(--ease-out);
}

.brief-highlight.is-marked::before {
  transform: none;
}

.brief-check {
  animation: brief-pop 240ms var(--ease-out) var(--pop-delay, 0ms) both;
}

/* Nace sobre el nombre de la fuente (mismo texto, ahora sobre lima), se despega y vuela hasta
   Rad, encogiéndose y fundiéndose al llegar. Una sola vez por pieza. */
.brief-pill {
  position: absolute;
  top: 50%;
  left: -8px;
  translate: 0 -50%;
  display: inline-flex;
  align-items: center;
  height: 26px;
  padding-inline: 8px;
  border-radius: 8px;
  background: var(--signal);
  color: var(--signal-foreground);
  font-weight: 600;
  white-space: nowrap;
  pointer-events: none;
  animation: brief-pill-fly 900ms var(--ease-out) 420ms both;
}

@media (prefers-reduced-motion: reduce) {
  .brief-highlight::before {
    transition: none;
  }

  .brief-check {
    animation: none;
  }

  .brief-pill {
    display: none;
  }
}

@keyframes brief-pop {
  from {
    opacity: 0;
    transform: scale(0.4);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@keyframes brief-pill-fly {
  0% {
    opacity: 0;
    transform: none;
  }
  20% {
    opacity: 1;
    transform: translateY(-4px);
  }
  100% {
    opacity: 0;
    transform: translate(var(--fly-x, 0px), var(--fly-y, 0px)) scale(0.3);
  }
}
</style>
