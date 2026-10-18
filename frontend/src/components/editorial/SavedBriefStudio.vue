<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useSavedBrief } from '@/api/editorial'
import { CARD_CLASS, SECONDARY_BUTTON_CLASS } from '@/components/dossier/dossierClasses'
import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'
import { useAuth } from '@/composables/useAuth'
import { serializeBriefQuery } from '@/lib/briefView'
import { PARENT_BRIEF_PARAM } from '@/lib/savedBriefs'
import { formatUtcTimestamp } from '@/lib/format'
import { cn } from '@/lib/utils'
import { RouteName } from '@/router/routeNames'
import { REDIRECT_PARAM } from '@/router/authGuard'

import BriefResult from './BriefResult.vue'
import BriefVersionSwitcher from './BriefVersionSwitcher.vue'

const { briefId } = defineProps<{ briefId: number }>()

const route = useRoute()
const router = useRouter()
const { isReady, isSignedIn } = useAuth()
const savedQuery = useSavedBrief(() => briefId)

const saved = computed(() => savedQuery.data.value ?? null)
const loginLink = computed(() => ({
  name: RouteName.Login,
  query: { [REDIRECT_PARAM]: route.fullPath },
}))

// Cambiar el enfoque vuelve al estudio del tema con las opciones de este brief, y lo que se genere
// allí será una versión nueva de este.
function editBrief() {
  if (saved.value === null) return
  void router.push({
    name: RouteName.Create,
    query: {
      ...serializeBriefQuery(saved.value.request),
      [PARENT_BRIEF_PARAM]: String(saved.value.id),
    },
  })
}
</script>

<template>
  <section
    v-if="isReady && !isSignedIn"
    aria-label="Brief guardado"
    :class="cn(CARD_CLASS, 'flex-col items-start')"
  >
    <RouterLink :to="loginLink" class="text-[15px] font-semibold underline underline-offset-4">
      Inicia sesión para ver este brief
    </RouterLink>
  </section>

  <div
    v-else-if="!isReady || savedQuery.isPending.value"
    class="flex flex-col gap-4"
    aria-busy="true"
  >
    <SkeletonBone class="h-[72px] rounded-card" />
    <SkeletonBone class="h-[420px] rounded-card" />
  </div>

  <section
    v-else-if="savedQuery.isError.value"
    aria-label="Brief guardado"
    :class="cn(CARD_CLASS, 'flex-col items-start gap-3')"
  >
    <p role="alert" class="text-[15px] text-ink-soft">No se pudo cargar el brief.</p>
    <button type="button" :class="SECONDARY_BUTTON_CLASS" @click="savedQuery.refetch()">
      Reintentar
    </button>
  </section>

  <section v-else-if="saved === null" aria-label="Brief guardado" :class="CARD_CLASS">
    <p class="text-[15px] text-ink-soft">Este brief no existe o es de otra cuenta.</p>
  </section>

  <div v-else class="flex flex-col gap-2">
    <div class="flex flex-wrap items-center justify-between gap-2 px-1">
      <p class="text-[13.5px] text-muted-foreground">
        Versión {{ saved.version }} · guardada el {{ formatUtcTimestamp(saved.created_at) }}
      </p>
      <BriefVersionSwitcher
        v-if="saved.versions.length > 1"
        :versions="saved.versions"
        :current-id="saved.id"
      />
    </div>
    <BriefResult :brief="saved.brief" @edit="editBrief" />
  </div>
</template>
