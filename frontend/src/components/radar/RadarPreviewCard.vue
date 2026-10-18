<script setup lang="ts">
import type { RankedOpportunity } from '@/lib/radarView'

import OpportunityPreview from './OpportunityPreview.vue'

const { opportunity, total } = defineProps<{ opportunity: RankedOpportunity; total: number }>()

const emit = defineEmits<{ clear: [] }>()
</script>

<template>
  <aside
    aria-label="Vista previa del tema"
    class="relative flex min-w-0 flex-col rounded-card bg-card xl:min-h-0"
  >
    <!-- La vista previa del tema ocupa el sitio del ranking, al lado del radar donde se eligió. Como
         el ranking, toma el alto del radar en escritorio y desplaza su contenido dentro. -->
    <div class="flex min-h-0 flex-1 flex-col overflow-auto p-[22px] xl:absolute xl:inset-0">
      <OpportunityPreview :opportunity :total @clear="emit('clear')" />
    </div>
  </aside>
</template>
