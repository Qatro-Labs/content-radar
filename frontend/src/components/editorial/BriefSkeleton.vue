<script setup lang="ts">
import { CARD_CLASS } from '@/components/dossier/dossierClasses'
import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'
import { countLabel } from '@/lib/evidenceFormat'

const { pieces } = defineProps<{ pieces: number | null }>()

// La forma exacta del brief: ángulo, gancho, cuatro pasos y dos puntos clave (DESIGN.md §4).
const SKELETON_STEPS = 4
const SKELETON_POINTS = 2
</script>

<template>
  <section
    aria-busy="true"
    aria-label="Redactando el brief"
    :class="[CARD_CLASS, 'flex-col gap-6']"
  >
    <!-- Sin spinner: una línea dice qué pasa y cuánto tarda (DESIGN.md §4 y §7). -->
    <p role="status" class="text-sm text-muted-foreground">
      <template v-if="pieces !== null">
        Redactando con {{ countLabel(pieces, 'pieza', 'piezas') }} de evidencia.
      </template>
      Tarda unos 15 s.
    </p>
    <div class="flex flex-col gap-2.5">
      <SkeletonBone class="h-4 w-40 rounded-full" />
      <SkeletonBone class="h-7 w-28 rounded-lg" />
      <SkeletonBone class="h-5 w-full max-w-[720px] rounded-full" />
      <SkeletonBone class="h-5 w-3/4 rounded-full" />
    </div>
    <div class="flex flex-col gap-2">
      <SkeletonBone class="h-5 w-20 rounded-full" />
      <SkeletonBone class="h-7 w-4/5 rounded-lg" />
    </div>
    <div class="flex flex-col gap-2">
      <SkeletonBone class="h-5 w-24 rounded-full" />
      <SkeletonBone v-for="step in SKELETON_STEPS" :key="step" class="h-5 w-2/3 rounded-full" />
    </div>
    <div class="flex flex-col gap-2">
      <SkeletonBone class="h-5 w-28 rounded-full" />
      <SkeletonBone v-for="point in SKELETON_POINTS" :key="point" class="h-20 rounded-tile" />
    </div>
  </section>
</template>
