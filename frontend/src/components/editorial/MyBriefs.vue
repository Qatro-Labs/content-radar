<script setup lang="ts">
import { ChevronRight } from '@lucide/vue'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { useSavedBriefs } from '@/api/editorial'
import { CARD_CLASS, SECONDARY_BUTTON_CLASS } from '@/components/dossier/dossierClasses'
import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'
import { useAuth } from '@/composables/useAuth'
import { parseSavedBriefId, SAVED_BRIEF_PARAM, savedBriefCaption } from '@/lib/savedBriefs'
import { cn } from '@/lib/utils'
import { REDIRECT_PARAM } from '@/router/authGuard'
import { RouteName } from '@/router/routeNames'

const SKELETON_ROWS = 3
const SECTION_TITLE_CLASS = 'text-[15px] font-semibold'

const route = useRoute()
const { isConfigured, isSignedIn } = useAuth()
const briefsQuery = useSavedBriefs()

const briefs = computed(() => briefsQuery.data.value ?? [])
const openedId = computed(() => parseSavedBriefId(route.query))
const loginLink = computed(() => ({
  name: RouteName.Login,
  query: { [REDIRECT_PARAM]: route.fullPath },
}))
</script>

<template>
  <!-- Sin Supabase no hay cuentas: la vista queda exactamente como sin login. -->
  <section
    v-if="isConfigured"
    aria-label="Mis briefs"
    :class="cn(CARD_CLASS, 'flex-col gap-3 py-5')"
  >
    <h2 :class="SECTION_TITLE_CLASS">Mis briefs</h2>

    <p v-if="!isSignedIn" class="text-[15px] text-ink-soft">
      <RouterLink
        :to="loginLink"
        class="font-semibold text-foreground underline underline-offset-4"
      >
        Inicia sesión para guardar tus briefs
      </RouterLink>
    </p>

    <div v-else-if="briefsQuery.isPending.value" class="flex flex-col gap-2" aria-busy="true">
      <SkeletonBone v-for="row in SKELETON_ROWS" :key="row" class="h-[52px] rounded-tile" />
    </div>

    <div v-else-if="briefsQuery.isError.value" class="flex flex-col items-start gap-3">
      <p role="alert" class="text-[15px] text-ink-soft">No se pudieron cargar tus briefs.</p>
      <button type="button" :class="SECONDARY_BUTTON_CLASS" @click="briefsQuery.refetch()">
        Reintentar
      </button>
    </div>

    <p v-else-if="briefs.length === 0" class="text-[15px] text-ink-soft">
      Todavía no has creado briefs.
    </p>

    <ul v-else class="flex flex-col">
      <li v-for="saved in briefs" :key="saved.id">
        <RouterLink
          :to="{ name: RouteName.Create, query: { [SAVED_BRIEF_PARAM]: String(saved.id) } }"
          :aria-current="saved.id === openedId ? 'page' : undefined"
          class="group flex min-h-[52px] items-center gap-3 border-t border-table-line px-3 py-2 transition-colors duration-150 ease-out hover:bg-sunken aria-[current=page]:bg-sunken"
        >
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="truncate text-[15px] leading-[1.35] font-medium">{{ saved.topic }}</span>
            <span class="text-[13px] text-muted-foreground">{{ savedBriefCaption(saved) }}</span>
          </span>
          <ChevronRight
            class="size-4 shrink-0 text-muted-foreground transition-colors duration-150 ease-out group-hover:text-foreground"
            aria-hidden="true"
          />
        </RouterLink>
      </li>
    </ul>
  </section>
</template>
