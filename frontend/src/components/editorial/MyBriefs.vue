<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useDeleteSavedBrief, useSavedBriefs } from '@/api/editorial'
import { canEdit, useWorkspace } from '@/api/workspace'
import { CARD_CLASS, SECONDARY_BUTTON_CLASS } from '@/components/dossier/dossierClasses'
import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'
import { parseSavedBriefId, SAVED_BRIEF_PARAM } from '@/lib/savedBriefs'
import { cn } from '@/lib/utils'

import SavedBriefRow from './SavedBriefRow.vue'

const SKELETON_ROWS = 3
const SECTION_TITLE_CLASS = 'text-[15px] font-semibold'

const route = useRoute()
const router = useRouter()
const workspaceQuery = useWorkspace()
const briefsQuery = useSavedBriefs()
const deletion = useDeleteSavedBrief()

const briefs = computed(() => briefsQuery.data.value ?? [])
const openedId = computed(() => parseSavedBriefId(route.query))
const canDelete = computed(() => canEdit(workspaceQuery.data.value))

// Si se borra el brief abierto, la vista vuelve al selector en lugar de decir que no existe.
async function removeBrief(id: number) {
  await deletion.mutateAsync(id).catch(() => undefined)
  if (deletion.isError.value || openedId.value !== id) return
  void router.replace({ query: { ...route.query, [SAVED_BRIEF_PARAM]: undefined } })
}
</script>

<template>
  <section aria-label="Briefs del equipo" :class="cn(CARD_CLASS, 'flex-col gap-3 py-5')">
    <h2 :class="SECTION_TITLE_CLASS">Briefs del equipo</h2>

    <div v-if="briefsQuery.isPending.value" class="flex flex-col gap-2" aria-busy="true">
      <SkeletonBone v-for="row in SKELETON_ROWS" :key="row" class="h-[52px] rounded-tile" />
    </div>

    <div v-else-if="briefsQuery.isError.value" class="flex flex-col items-start gap-3">
      <p role="alert" class="text-[15px] text-ink-soft">
        No se pudieron cargar los briefs del equipo.
      </p>
      <button type="button" :class="SECONDARY_BUTTON_CLASS" @click="briefsQuery.refetch()">
        Reintentar
      </button>
    </div>

    <p v-else-if="briefs.length === 0" class="text-[15px] text-ink-soft">
      Todavía no hay briefs del equipo.
    </p>

    <template v-else>
      <p v-if="deletion.isError.value" role="alert" class="text-[15px] text-ink-soft">
        No se pudo borrar el brief.
      </p>
      <ul class="flex flex-col">
        <SavedBriefRow
          v-for="saved in briefs"
          :key="saved.id"
          :saved
          :is-open="saved.id === openedId"
          :is-deleting="deletion.isPending.value"
          :can-delete
          @delete="removeBrief(saved.id)"
        />
      </ul>
    </template>
  </section>
</template>
