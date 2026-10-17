<script setup lang="ts">
import { formatUtcTimestamp } from '@/lib/format'

const { monitoringStartedAt } = defineProps<{ monitoringStartedAt: string }>()
</script>

<template>
  <!-- DESIGN.md §9: desde cuándo se monitorea va siempre a la vista, y el encaje y la saturación
       se rotulan para que no se lean como mediciones absolutas (CLAUDE.md §2.3). -->
  <p class="px-1 text-[13.5px] text-muted-foreground">
    Datos desde el {{ formatUtcTimestamp(monitoringStartedAt) }}. Las burbujas que laten están
    creciendo: cuanto más rápido laten, más aceleran. El tamaño indica la fuerza de la evidencia. La
    saturación se mide dentro de las fuentes monitoreadas. El encaje es una evaluación editorial, no
    una medición.
  </p>
</template>
