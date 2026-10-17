<script setup lang="ts">
import { SWEEP } from '@/lib/radarChart'

// Los mismos tiempos y ángulos que `sweepDelaySeconds`: cada burbuja aparece cuando el haz la cruza.
const beamTiming = {
  '--sweep-from': `${SWEEP.fromDeg}deg`,
  '--sweep-to': `${SWEEP.toDeg}deg`,
  animationDuration: `${SWEEP.durationMs}ms`,
  animationDelay: `${SWEEP.delayMs}ms`,
}
</script>

<template>
  <div class="pointer-events-none absolute inset-0 overflow-hidden rounded-tile" aria-hidden="true">
    <div class="radar-beam" :style="beamTiming" />
  </div>
</template>

<style scoped>
/* DESIGN.md §7: el haz pivota en la esquina "Prioridad" con una estela del lavado de señal. Es el
   único gradiente permitido (§10), y solo existe mientras dura el barrido. */
.radar-beam {
  position: absolute;
  top: 0;
  left: 100%;
  width: 260%;
  aspect-ratio: 1 / 1;
  background: conic-gradient(
    from 0deg,
    transparent 0deg,
    transparent 300deg,
    color-mix(in srgb, var(--signal) 34%, transparent) 358deg,
    color-mix(in srgb, var(--foreground) 40%, transparent) 359.2deg,
    transparent 360deg
  );
  opacity: 0;
  transform: translate(-50%, -50%) rotate(var(--sweep-from));
  animation-name: radar-sweep;
  animation-timing-function: linear;
  animation-fill-mode: both;
}

@media (prefers-reduced-motion: reduce) {
  .radar-beam {
    animation: none;
  }
}

@keyframes radar-sweep {
  0% {
    opacity: 1;
    transform: translate(-50%, -50%) rotate(var(--sweep-from));
  }
  82% {
    opacity: 1;
  }
  100% {
    opacity: 0;
    transform: translate(-50%, -50%) rotate(var(--sweep-to));
  }
}
</style>
