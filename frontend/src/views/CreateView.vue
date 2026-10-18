<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import CreateStudio from '@/components/editorial/CreateStudio.vue'
import CreateTopicPicker from '@/components/editorial/CreateTopicPicker.vue'
import MyBriefs from '@/components/editorial/MyBriefs.vue'
import SavedBriefStudio from '@/components/editorial/SavedBriefStudio.vue'
import { useAuth } from '@/composables/useAuth'
import { parseBriefQuery } from '@/lib/briefView'
import { parseSavedBriefId } from '@/lib/savedBriefs'

const route = useRoute()
const { isConfigured } = useAuth()
const opportunityId = computed(() => parseBriefQuery(route.query).opportunityId)
// Sin cuentas no hay briefs guardados: `?brief=` se ignora y la vista sigue como siempre.
const savedBriefId = computed(() => (isConfigured ? parseSavedBriefId(route.query) : null))
// El estudio y el brief guardado van en una columna de 880 px; el selector de temas, a lo ancho.
const isSingleColumn = computed(() => savedBriefId.value !== null || opportunityId.value !== null)
</script>

<template>
  <div class="flex flex-col gap-5">
    <!-- Un brief guardado se abre por su id; si no, sin tema la vista propone de qué escribir y
         con tema prepara su brief. -->
    <div v-if="savedBriefId !== null" class="mx-auto flex w-full max-w-[880px] flex-col pt-5">
      <SavedBriefStudio :key="savedBriefId" :brief-id="savedBriefId" />
    </div>
    <CreateTopicPicker v-else-if="opportunityId === null" />
    <!-- Por tema: otro tema empieza en blanco, sin el brief del anterior. -->
    <CreateStudio v-else :key="opportunityId" :opportunity-id="opportunityId" />

    <div :class="isSingleColumn ? 'mx-auto w-full max-w-[880px]' : 'w-full'">
      <MyBriefs />
    </div>
  </div>
</template>
