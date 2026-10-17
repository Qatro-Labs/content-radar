<script setup lang="ts">
import { useLatestObservation } from '@/api/sources'
import { formatUtcTimestamp } from '@/lib/format'

const { data: latest, isPending, isError } = useLatestObservation()
</script>

<template>
  <p class="text-[13px] text-muted-foreground" aria-live="polite">
    <span
      v-if="isPending"
      class="block h-4 w-52 animate-pulse rounded-full bg-track"
      aria-label="Cargando estado de los datos"
    />
    <template v-else-if="isError">Estado de los datos no disponible</template>
    <template v-else-if="latest">Última recolección: {{ formatUtcTimestamp(latest) }}</template>
    <template v-else>Todavía no hay recolecciones</template>
  </p>
</template>
