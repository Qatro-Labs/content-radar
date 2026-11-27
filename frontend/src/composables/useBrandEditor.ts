import { computed, ref, shallowRef, watch } from 'vue'

import { useSavedBrief, useSavedBriefs } from '@/api/editorial'
import { canEdit, useProfile, useSaveProfile, useWorkspace } from '@/api/workspace'
import {
  draftErrors,
  isDirty,
  previewOf,
  toDraft,
  toSavedProfile,
  type BrandDraft,
} from '@/lib/brandProfile'
import type { components } from '@/types/api'

type ProfileRead = components['schemas']['ProfileRead']

export const BrandNoticeKind = {
  LoadError: 'load_error',
  ReadOnly: 'read_only',
  Conflict: 'conflict',
  SaveError: 'save_error',
  Saved: 'saved',
} as const
export type BrandNoticeKind = (typeof BrandNoticeKind)[keyof typeof BrandNoticeKind]

// Estado de «Tu marca»: el borrador, contra qué versión se guarda y qué aviso toca enseñar.
export function useBrandEditor() {
  const workspaceQuery = useWorkspace()
  const profileQuery = useProfile()
  const save = useSaveProfile()

  // R4: la vista previa usa el último brief guardado del equipo (la lista llega del más reciente
  // al más antiguo); sin briefs, el ejemplo.
  const briefsQuery = useSavedBriefs()
  const latestBriefId = computed(() => briefsQuery.data.value?.[0]?.id ?? null)
  const latestBriefQuery = useSavedBrief(latestBriefId)

  const baseline = shallowRef<ProfileRead | null>(null)
  const draft = ref<BrandDraft | null>(null)

  function adopt(read: ProfileRead) {
    baseline.value = read
    draft.value = toDraft(read.profile)
  }

  const editable = computed(() => canEdit(workspaceQuery.data.value))
  const workspaceName = computed(() => workspaceQuery.data.value?.name ?? '')
  const loadFailed = computed(() => profileQuery.isError.value || workspaceQuery.isError.value)
  const isLoading = computed(
    () => !loadFailed.value && (draft.value === null || workspaceQuery.isPending.value),
  )
  const dirty = computed(
    () =>
      draft.value !== null &&
      baseline.value !== null &&
      isDirty(draft.value, baseline.value.profile),
  )
  // Una recarga en segundo plano solo sustituye un borrador sin cambios: lo escrito no se pierde,
  // y si otro guardó antes, el guardado dará 409.
  watch(
    () => profileQuery.data.value,
    (read) => {
      if (read === undefined) return
      if (draft.value === null || !dirty.value) adopt(read)
    },
    { immediate: true },
  )

  const errors = computed(() => (draft.value === null ? {} : draftErrors(draft.value)))
  const canSave = computed(
    () =>
      editable.value &&
      dirty.value &&
      Object.keys(errors.value).length === 0 &&
      !save.isPending.value,
  )
  const preview = computed(() =>
    draft.value === null
      ? null
      : previewOf(draft.value, latestBriefQuery.data.value?.brief ?? null),
  )

  const notice = computed<BrandNoticeKind | null>(() => {
    if (loadFailed.value) return BrandNoticeKind.LoadError
    if (isLoading.value) return null
    if (!editable.value) return BrandNoticeKind.ReadOnly
    if (save.conflict.value) return BrandNoticeKind.Conflict
    if (save.isError.value) return BrandNoticeKind.SaveError
    if (save.isSuccess.value && !dirty.value) return BrandNoticeKind.Saved
    return null
  })
  const conflictMessage = computed(() => save.error.value?.message ?? '')

  async function submit(): Promise<boolean> {
    if (!canSave.value || draft.value === null || baseline.value === null) return false
    try {
      adopt(
        await save.mutateAsync({
          profile: toSavedProfile(draft.value),
          expected_version: baseline.value.version,
        }),
      )
      return true
    } catch {
      // El aviso de error o de conflicto sale del estado de la mutación.
      return false
    }
  }

  // Tras un 409, recargar trae la versión del otro miembro y descarta el borrador: por eso el aviso
  // pide copiar antes lo que se quiera conservar.
  async function reload() {
    save.reset()
    if (loadFailed.value) void workspaceQuery.refetch()
    const { data } = await profileQuery.refetch()
    if (data !== undefined) adopt(data)
  }

  return {
    draft,
    editable,
    workspaceName,
    isLoading,
    dirty,
    errors,
    canSave,
    isSaving: save.isPending,
    preview,
    notice,
    conflictMessage,
    submit,
    reload,
  }
}
