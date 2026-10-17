<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import { LIFECYCLE_STYLE } from '@/lib/lifecycle'
import { formatAcceleration, formatScore } from '@/lib/opportunityFormat'
import {
  bubblePosition,
  detectionDelayMs,
  isPlotted,
  shownBubbleSize,
  type PlotPoint,
  type PlotSize,
  type PlottedOpportunity,
} from '@/lib/radarChart'
import type { RankedOpportunity } from '@/lib/radarView'

const { selected, hovered, size } = defineProps<{
  selected: RankedOpportunity | null
  hovered: RankedOpportunity | null
  size: PlotSize
}>()

// DESIGN.md §7: tres ondas del trazo de la etapa, separadas 160 ms.
const PING_WAVES = [0, 1, 2]
const PING_STAGGER_MS = 160
// Artboard E: la tarjeta va a 26 px de la burbuja y, con encaje > 62, a su izquierda, porque a la
// derecha ya no cabe.
const CARD_GAP_PX = 26
const CARD_FLIP_FIT_MIN = 62
// Un instante después de que el haz detecte la burbuja, cuando ya empieza a aparecer.
const AFTER_DETECTION_MS = 50
// DESIGN.md §7: la mira, las lecturas, los anillos y la tarjeta se deslizan en 320 ms, solo con
// `transform`; el centrado va en `translate`, aparte, y sigue al diámetro sin deslizarse.
const SLIDE = 'transition-transform duration-[320ms] ease-out motion-reduce:transition-none'
// DESIGN.md §8: anillo de Tinta de 2 px separado por 2 px de blanco.
const RING = 'absolute top-0 left-0 z-[3] -translate-1/2 rounded-full ring-2 ring-offset-2'
const READING =
  'absolute z-[3] rounded-[6px] bg-primary px-1.5 py-px text-xs font-semibold whitespace-nowrap text-primary-foreground'

interface Spot {
  opportunity: PlottedOpportunity
  point: PlotPoint
  diameter: number
}

// Una oportunidad sin encaje (seleccionada desde el ranking) no tiene burbuja que marcar.
function spotOf(opportunity: RankedOpportunity | null): Spot | null {
  if (!opportunity || !isPlotted(opportunity) || size.width === 0 || size.height === 0) return null
  const focus = { selectedId: selected?.id ?? null, hoveredId: hovered?.id ?? null }
  return {
    opportunity,
    point: bubblePosition(opportunity, size),
    diameter: shownBubbleSize(opportunity, focus),
  }
}

// El radar se remonta con cada barrido (al cargar y al cambiar de periodo). La primera selección
// espera a que el haz detecte su burbuja (DESIGN.md §7); las siguientes responden al instante.
const isFirstSelection = ref(true)
watch(
  () => selected?.id,
  (_, previousId) => {
    if (previousId) isFirstSelection.value = false
  },
)

const translateTo = ({ x, y }: PlotPoint) => `translate(${x}px, ${y}px)`

function ringBox({ point, diameter }: Spot) {
  return { width: `${diameter}px`, height: `${diameter}px`, transform: translateTo(point) }
}

function cardSide({ opportunity }: Spot): string {
  if (opportunity.audience_fit_score > CARD_FLIP_FIT_MIN) {
    return `translate(calc(-100% - ${CARD_GAP_PX}px), -50%)`
  }
  return `translate(${CARD_GAP_PX}px, -50%)`
}

const layout = computed(() => {
  const spot = spotOf(selected)
  if (!spot) return null
  const { x, y } = spot.point
  const delayMs = isFirstSelection.value
    ? detectionDelayMs(spot.opportunity) + AFTER_DETECTION_MS
    : 0
  return {
    spot,
    delayMs,
    horizontal: { transform: `translateY(${y}px) scaleX(${x / size.width})` },
    vertical: {
      transform: `${translateTo(spot.point)} scaleY(${(size.height - y) / size.height})`,
    },
    momentumReading: { transform: `translateY(calc(${y}px - 50%))` },
    fitReading: { transform: `translateX(calc(${x}px - 50%))` },
    ring: { ...ringBox(spot), animationDelay: `${delayMs}ms` },
    card: {
      transform: `${translateTo(spot.point)} ${cardSide(spot)}`,
      animationDelay: `${delayMs}ms`,
    },
    pingColor: `var(${LIFECYCLE_STYLE[spot.opportunity.lifecycle].cssVar.stroke})`,
  }
})

// La seleccionada ya lleva su anillo: el de hover sería redundante.
const hoverSpot = computed(() => (hovered?.id === selected?.id ? null : spotOf(hovered)))
</script>

<template>
  <div class="pointer-events-none absolute inset-0" aria-hidden="true">
    <template v-if="layout">
      <span
        class="absolute top-0 left-0 z-[1] h-px w-full origin-left bg-foreground/28"
        :class="SLIDE"
        :style="layout.horizontal"
      />
      <span
        class="absolute top-0 left-0 z-[1] h-full w-px origin-top bg-foreground/28"
        :class="SLIDE"
        :style="layout.vertical"
      />
      <span
        :class="[READING, SLIDE, 'top-0 right-[calc(100%+4px)]']"
        :style="layout.momentumReading"
      >
        {{ formatScore(layout.spot.opportunity.momentum_score) }}
      </span>
      <span :class="[READING, SLIDE, 'top-[calc(100%+5px)] left-0']" :style="layout.fitReading">
        {{ formatScore(layout.spot.opportunity.audience_fit_score) }}
      </span>
      <span
        :class="[RING, SLIDE, 'ring-foreground', { 'radar-entry': isFirstSelection }]"
        :style="layout.ring"
      />
      <div
        :key="layout.spot.opportunity.id"
        class="absolute top-0 left-0 z-[3]"
        :style="{ transform: translateTo(layout.spot.point) }"
      >
        <span
          v-for="wave in PING_WAVES"
          :key="wave"
          class="radar-ping"
          :style="{
            width: `${layout.spot.diameter}px`,
            height: `${layout.spot.diameter}px`,
            borderColor: layout.pingColor,
            animationDelay: `${layout.delayMs + wave * PING_STAGGER_MS}ms`,
          }"
        />
      </div>
      <div
        class="absolute top-0 left-0 z-[4] flex w-60 flex-col gap-1.5 rounded-tile bg-card px-3.5 py-3 shadow-float"
        :class="[SLIDE, { 'radar-entry': isFirstSelection }]"
        :style="layout.card"
      >
        <LifecycleChip
          :lifecycle="layout.spot.opportunity.lifecycle"
          size="sm"
          class="self-start"
        />
        <span class="text-[15px] leading-tight font-semibold">
          {{ layout.spot.opportunity.topic }}
        </span>
        <!-- Etiqueta (#4A505A, DESIGN.md §2) no tiene token en main.css. -->
        <span class="text-[13px] text-[#4a505a]">
          Oportunidad {{ formatScore(layout.spot.opportunity.opportunity_score) }} ·
          {{ formatAcceleration(layout.spot.opportunity.acceleration) }}
        </span>
      </div>
    </template>
    <span
      v-if="hoverSpot"
      :class="[RING, SLIDE, 'ring-foreground/30']"
      :style="ringBox(hoverSpot)"
    />
  </div>
</template>

<style scoped>
/* DESIGN.md §7: tres ondas de 1,1 s que se escalan ×4,6. Sin movimiento, no hay ping. */
.radar-ping {
  position: absolute;
  top: 0;
  left: 0;
  translate: -50% -50%;
  border: 1.5px solid;
  border-radius: 9999px;
  opacity: 0;
  animation: radar-ping 1100ms cubic-bezier(0.2, 0.6, 0.35, 1) forwards;
}

.radar-entry {
  animation: radar-entry 260ms var(--ease-out) both;
}

@media (prefers-reduced-motion: reduce) {
  .radar-ping,
  .radar-entry {
    animation: none;
  }
}

@keyframes radar-ping {
  from {
    opacity: 0.75;
    transform: scale(1);
  }
  to {
    opacity: 0;
    transform: scale(4.6);
  }
}

@keyframes radar-entry {
  from {
    opacity: 0;
  }
}
</style>
