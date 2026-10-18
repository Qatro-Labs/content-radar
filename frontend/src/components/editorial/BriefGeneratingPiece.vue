<script setup lang="ts">
import { Check } from '@lucide/vue'
import { computed, ref, useTemplateRef, watch } from 'vue'

import { AGENT_ROOT_SELECTOR } from '@/lib/agentTargets'
import { ABSORB_MS, type PieceStatus } from '@/lib/briefStages'
import { PLATFORM_LABEL, shortSourceName } from '@/lib/evidenceFormat'
import type { components } from '@/types/api'

interface Point {
  x: number
  y: number
}

const { piece, status, absorbed, absorbDelayMs } = defineProps<{
  piece: components['schemas']['Evidence']
  status: PieceStatus
  // Leídas todas, la pieza vuela hasta Rad y desaparece en él.
  absorbed: boolean
  absorbDelayMs: number
}>()

// La marca de Rad de la tarjeta (BriefGenerating), destino de la fuente que vuela y de la pieza.
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
const root = useTemplateRef<HTMLElement>('root')
const pill = useTemplateRef<HTMLElement>('pill')
const flight = ref<Point | null>(null)
const toRad = ref<Point | null>(null)

function centerOf(rect: DOMRect): Point {
  return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 }
}

// FLIP: se mide dónde está el elemento y dónde está Rad, y el viaje lo hace `transform`; las
// variables CSS llevan el desplazamiento a la animación.
function offsetToRad(element: HTMLElement): Point | null {
  const mark = element.closest(AGENT_ROOT_SELECTOR)?.querySelector(RAD_MARK_SELECTOR)
  if (!mark) return null
  const from = centerOf(element.getBoundingClientRect())
  const to = centerOf(mark.getBoundingClientRect())
  return { x: to.x - from.x, y: to.y - from.y }
}

watch(pill, (element) => {
  if (element) flight.value = offsetToRad(element)
})
// Se mide antes de pintar la clase: con ella puesta, la pieza ya estaría de camino.
watch(
  () => absorbed,
  (isAbsorbed) => {
    if (isAbsorbed && root.value) toRad.value = offsetToRad(root.value)
  },
  { flush: 'pre' },
)

const flightStyle = computed(() =>
  flight.value ? { '--fly-x': `${flight.value.x}px`, '--fly-y': `${flight.value.y}px` } : {},
)
const absorbStyle = computed(() => ({
  '--absorb-x': `${toRad.value?.x ?? 0}px`,
  '--absorb-y': `${toRad.value?.y ?? 0}px`,
  '--absorb-delay': `${absorbDelayMs}ms`,
  '--absorb-duration': `${ABSORB_MS}ms`,
}))
</script>

<template>
  <li
    ref="root"
    class="brief-piece flex min-h-[132px] min-w-0 flex-col gap-2 rounded-tile bg-sunken px-4 py-3.5"
    :class="{ 'is-reading': status === 'reading', 'is-absorbed': absorbed }"
    :style="absorbStyle"
  >
    <span class="flex items-start gap-2">
      <!-- Sin `truncate`: su overflow recortaría la píldora que sale volando. -->
      <span class="min-w-0 grow text-[13px] leading-snug text-label">
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
    </span>
    <!-- El subrayado pasa por el título real: Rad no se inventa qué frase se lleva. Texto
         externo interpolado, nunca como HTML (CLAUDE.md §2.6). -->
    <p class="line-clamp-3 text-[15px] leading-[1.45] font-semibold">
      <span class="brief-highlight" :class="{ 'is-marked': isStarted }">{{ piece.title }}</span>
    </p>
  </li>
</template>

<style scoped>
.brief-piece {
  transition: transform 300ms var(--ease-out);
}

.brief-piece.is-reading {
  transform: translateY(-6px);
}

/* Artboard C1: leídas todas, las piezas vuelan escalonadas hasta Rad, encogiéndose y fundiéndose.
   Acelera al final, como si Rad las atrajera; sin pausas ni rebotes. */
.brief-piece.is-absorbed {
  pointer-events: none;
  opacity: 0;
  transform: translate(var(--absorb-x), var(--absorb-y)) scale(0.12);
  transition:
    transform var(--absorb-duration) cubic-bezier(0.7, 0, 0.84, 0) var(--absorb-delay),
    opacity var(--absorb-duration) cubic-bezier(0.7, 0, 0.84, 0) var(--absorb-delay);
}

/* Rotulador lima bajo el título (C1). Una capa con `scaleX` no sigue las líneas de un título
   que ocupa varias: el fondo crece en ancho y, como el inline se pinta de corrido, pasa línea a
   línea como un rotulador de verdad. Un solo color, no un degradado (DESIGN.md §10). */
.brief-highlight {
  background-image: linear-gradient(
    color-mix(in srgb, var(--signal) 75%, transparent),
    color-mix(in srgb, var(--signal) 75%, transparent)
  );
  background-repeat: no-repeat;
  background-position: 0 88%;
  background-size: 0% 44%;
  transition: background-size 650ms var(--ease-out);
}

.brief-highlight.is-marked {
  background-size: 100% 44%;
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
  .brief-piece,
  .brief-piece.is-absorbed,
  .brief-highlight {
    transition: none;
  }

  .brief-piece.is-reading,
  .brief-piece.is-absorbed {
    transform: none;
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
