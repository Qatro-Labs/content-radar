<script setup lang="ts">
import { useId } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { SAVED_BRIEF_PARAM, versionLabel } from '@/lib/savedBriefs'
import type { components } from '@/types/api'

const { versions, currentId } = defineProps<{
  versions: components['schemas']['BriefVersion'][]
  currentId: number
}>()

const route = useRoute()
const router = useRouter()
const selectId = useId()

// Cada versión es su propio `?brief=`: el enlace abre esa versión exacta.
function openVersion(event: Event) {
  if (!(event.target instanceof HTMLSelectElement)) return
  void router.push({ query: { ...route.query, [SAVED_BRIEF_PARAM]: event.target.value } })
}
</script>

<template>
  <div class="flex min-w-0 items-center gap-2">
    <label :for="selectId" class="text-[13px] font-semibold text-label">Versión</label>
    <select
      :id="selectId"
      :value="String(currentId)"
      class="h-9 max-w-full min-w-0 rounded-[10px] bg-card px-2.5 text-[13.5px] text-foreground"
      @change="openVersion"
    >
      <option v-for="version in versions" :key="version.id" :value="String(version.id)">
        {{ versionLabel(version) }}
      </option>
    </select>
  </div>
</template>
