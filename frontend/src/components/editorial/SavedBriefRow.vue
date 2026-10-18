<script setup lang="ts">
import { ChevronRight, Trash2 } from '@lucide/vue'
import { computed, ref } from 'vue'

import { PRIMARY_BUTTON_CLASS, SECONDARY_BUTTON_CLASS } from '@/components/dossier/dossierClasses'
import {
  deleteConfirmation,
  SAVED_BRIEF_PARAM,
  savedBriefCaption,
  versionCountLabel,
} from '@/lib/savedBriefs'
import { RouteName } from '@/router/routeNames'
import type { components } from '@/types/api'

const { saved, isOpen, isDeleting } = defineProps<{
  saved: components['schemas']['SavedBriefSummary']
  isOpen: boolean
  isDeleting: boolean
}>()

const emit = defineEmits<{ delete: [] }>()

// Borrar quita todas las versiones: se pide confirmación en la propia fila.
const isConfirming = ref(false)
const versions = computed(() => versionCountLabel(saved.version_count))

function confirmDelete() {
  isConfirming.value = false
  emit('delete')
}
</script>

<template>
  <li class="flex flex-col border-t border-table-line">
    <div class="flex items-center gap-1">
      <RouterLink
        :to="{ name: RouteName.Create, query: { [SAVED_BRIEF_PARAM]: String(saved.id) } }"
        :aria-current="isOpen ? 'page' : undefined"
        class="group flex min-h-[52px] min-w-0 flex-1 items-center gap-3 rounded-tile px-3 py-2 transition-colors duration-150 ease-out hover:bg-sunken aria-[current=page]:bg-sunken"
      >
        <span class="flex min-w-0 flex-1 flex-col">
          <span class="truncate text-[15px] leading-[1.35] font-medium">{{ saved.topic }}</span>
          <span class="flex flex-wrap items-center gap-2 text-[13px] text-muted-foreground">
            {{ savedBriefCaption(saved) }}
            <span
              v-if="versions"
              class="rounded-full bg-secondary px-2 py-0.5 text-[12px] font-semibold text-secondary-foreground"
            >
              {{ versions }}
            </span>
          </span>
        </span>
        <ChevronRight
          class="size-4 shrink-0 text-muted-foreground transition-colors duration-150 ease-out group-hover:text-foreground"
          aria-hidden="true"
        />
      </RouterLink>
      <button
        type="button"
        :aria-label="`Borrar el brief «${saved.topic}»`"
        :disabled="isDeleting"
        class="inline-flex size-11 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors duration-150 ease-out hover:bg-secondary-hover hover:text-foreground disabled:opacity-50"
        @click="isConfirming = true"
      >
        <Trash2 class="size-4" aria-hidden="true" />
      </button>
    </div>

    <div
      v-if="isConfirming"
      role="alertdialog"
      :aria-label="`Borrar el brief «${saved.topic}»`"
      class="mb-2 flex flex-wrap items-center gap-2 rounded-tile bg-sunken px-3 py-2.5"
    >
      <p class="min-w-0 flex-1 text-sm text-ink-read">{{ deleteConfirmation(saved) }}</p>
      <button type="button" :class="SECONDARY_BUTTON_CLASS" @click="isConfirming = false">
        Cancelar
      </button>
      <button type="button" :class="PRIMARY_BUTTON_CLASS" @click="confirmDelete">Borrar</button>
    </div>
  </li>
</template>
