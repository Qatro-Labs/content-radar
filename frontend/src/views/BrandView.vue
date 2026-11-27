<script setup lang="ts">
import { useEventListener } from '@vueuse/core'
import { computed, shallowRef } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'

import BrandForm from '@/components/brand/BrandForm.vue'
import BrandNotice, { type NoticeTone } from '@/components/brand/BrandNotice.vue'
import BrandPreview from '@/components/brand/BrandPreview.vue'
import { PRIMARY_BUTTON_CLASS, SECONDARY_BUTTON_CLASS } from '@/components/dossier/dossierClasses'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogTitle,
} from '@/components/ui/dialog'
import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'
import { useAuth } from '@/composables/useAuth'
import { BrandNoticeKind, useBrandEditor } from '@/composables/useBrandEditor'
import { REDIRECT_PARAM } from '@/router/authGuard'
import { RouteName } from '@/router/routeNames'

const route = useRoute()
const router = useRouter()
const { isConfigured, isReady, isSignedIn } = useAuth()
const editor = useBrandEditor()
const { draft, editable, isLoading, dirty, errors, canSave, isSaving, preview, notice } = editor

// El aviso de botón contorneado sigue al de la propuesta A: hereda el color del aviso.
const NOTICE_ACTION_CLASS =
  'inline-flex min-h-10 items-center rounded-[10px] border border-current px-3.5 text-sm font-semibold transition-opacity duration-150 ease-out hover:opacity-80'

const subtitle = computed(() =>
  editable.value || isLoading.value
    ? 'Cambia algo a la izquierda y mira a la derecha cómo cambiaría tu próximo brief.'
    : 'Así describe su marca el equipo. Cada brief que generes lo sigue.',
)
const canSignIn = computed(() => isConfigured && isReady.value && !isSignedIn.value)

interface NoticeCopy {
  tone: NoticeTone
  title: string
  text: string
}
const noticeCopy = computed<NoticeCopy | null>(() => {
  switch (notice.value) {
    case BrandNoticeKind.Saved:
      return {
        tone: 'success',
        title: 'Guardado.',
        text: 'Tus próximos briefs usarán este perfil.',
      }
    case BrandNoticeKind.SaveError:
      return {
        tone: 'danger',
        title: 'No se pudo guardar.',
        text: 'Revisa tu conexión. Tus cambios siguen aquí.',
      }
    case BrandNoticeKind.Conflict:
      return {
        tone: 'danger',
        title: editor.conflictMessage.value,
        text: 'Copia antes lo que quieras conservar.',
      }
    case BrandNoticeKind.ReadOnly:
      return {
        tone: 'info',
        title: `Estás viendo el perfil de ${editor.workspaceName.value}.`,
        text: 'Solo su equipo puede cambiarlo.',
      }
    case BrandNoticeKind.LoadError:
      return {
        tone: 'danger',
        title: 'No se pudo cargar el perfil.',
        text: 'El radar y los briefs siguen funcionando.',
      }
    default:
      return null
  }
})

// Salir con cambios sin guardar pide confirmación, dentro de la app y al cerrar la pestaña.
const hasUnsavedChanges = computed(() => editable.value && dirty.value)
const pendingLeave = shallowRef<string | null>(null)
let leaveConfirmed = false

onBeforeRouteLeave((to) => {
  if (leaveConfirmed || !hasUnsavedChanges.value) return true
  pendingLeave.value = to.fullPath
  return false
})
useEventListener(window, 'beforeunload', (event: BeforeUnloadEvent) => {
  if (hasUnsavedChanges.value) event.preventDefault()
})

async function leave() {
  const target = pendingLeave.value
  pendingLeave.value = null
  if (target === null) return
  leaveConfirmed = true
  await router.push(target)
}

async function saveAndLeave() {
  if (await editor.submit()) return leave()
  // Si falla, el diálogo se cierra para que se vea el aviso y el borrador siga ahí.
  pendingLeave.value = null
}

function onDialogOpen(open: boolean) {
  if (!open) pendingLeave.value = null
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-[1160px] flex-col gap-4 pt-2">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div class="flex max-w-[720px] flex-col gap-2">
        <span v-if="editor.workspaceName.value" class="text-[13px] font-semibold text-label">
          {{ editor.workspaceName.value }}
        </span>
        <h1
          class="font-display text-[clamp(2.25rem,4vw,3.5rem)] leading-none font-semibold tracking-[-0.04em]"
        >
          Tu marca
        </h1>
        <p class="text-[15px] leading-normal text-ink-soft">{{ subtitle }}</p>
      </div>
      <button
        v-if="editable && !isLoading"
        type="button"
        :class="[
          PRIMARY_BUTTON_CLASS,
          'disabled:bg-window-previous disabled:text-muted-foreground',
        ]"
        :disabled="!canSave"
        :aria-busy="isSaving"
        @click="editor.submit"
      >
        {{ dirty ? 'Guardar cambios ●' : 'Guardar cambios' }}
      </button>
    </div>

    <BrandNotice v-if="noticeCopy" v-bind="noticeCopy">
      <button
        v-if="notice === BrandNoticeKind.SaveError"
        type="button"
        :class="NOTICE_ACTION_CLASS"
        @click="editor.submit"
      >
        Reintentar
      </button>
      <button
        v-else-if="notice === BrandNoticeKind.Conflict || notice === BrandNoticeKind.LoadError"
        type="button"
        :class="NOTICE_ACTION_CLASS"
        @click="editor.reload"
      >
        {{ notice === BrandNoticeKind.Conflict ? 'Recargar' : 'Reintentar' }}
      </button>
      <RouterLink
        v-else-if="notice === BrandNoticeKind.ReadOnly && canSignIn"
        :to="{ name: RouteName.Login, query: { [REDIRECT_PARAM]: route.fullPath } }"
        :class="NOTICE_ACTION_CLASS"
      >
        Iniciar sesión
      </RouterLink>
    </BrandNotice>

    <div v-if="isLoading" aria-busy="true" class="flex flex-wrap gap-5">
      <span class="sr-only">Cargando el perfil de tu marca…</span>
      <div class="flex flex-[999_1_460px] flex-col gap-3">
        <SkeletonBone class="h-[230px] rounded-card" />
        <SkeletonBone class="h-[230px] rounded-card" />
        <SkeletonBone class="h-[110px] rounded-card" />
      </div>
      <SkeletonBone class="h-[460px] flex-[1_1_380px] rounded-[24px]" />
    </div>

    <div v-else-if="draft && preview" class="flex flex-wrap items-start gap-5">
      <BrandForm v-model="draft" :editable="editable" :errors="errors" />
      <BrandPreview :preview="preview" :editable="editable" />
    </div>

    <Dialog :open="pendingLeave !== null" @update:open="onDialogOpen">
      <DialogContent :show-close-button="false">
        <DialogTitle class="text-xl font-semibold">¿Salir sin guardar?</DialogTitle>
        <DialogDescription class="text-[15px] leading-[1.45] text-ink-soft">
          Tienes cambios sin guardar en tu marca. Si sales ahora, se pierden.
        </DialogDescription>
        <DialogFooter class="flex flex-wrap justify-end gap-2">
          <button type="button" :class="SECONDARY_BUTTON_CLASS" @click="leave">
            Salir sin guardar
          </button>
          <button
            type="button"
            :class="PRIMARY_BUTTON_CLASS"
            :disabled="!canSave"
            @click="saveAndLeave"
          >
            Guardar y salir
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
