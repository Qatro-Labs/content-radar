<template>
  <span class="dossier-bone block" aria-hidden="true" />
</template>

<style scoped>
/* DESIGN.md §4: los skeletons van de Pista a Lienzo en 1,6 s, sin spinners. Con movimiento
   reducido se quedan quietos (§7). La forma (alto, ancho, radio) la pone quien lo usa. */
.dossier-bone {
  background-color: var(--track);
  animation: dossier-bone 1.6s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  .dossier-bone {
    animation: none;
  }
}

@keyframes dossier-bone {
  50% {
    background-color: var(--background);
  }
}
</style>
