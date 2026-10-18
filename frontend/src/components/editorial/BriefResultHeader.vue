<script setup lang="ts">
import { Check, Copy, Link } from '@lucide/vue'
import { useClipboard } from '@vueuse/core'
import { computed, ref } from 'vue'

import { PRIMARY_BUTTON_CLASS, SECONDARY_BUTTON_CLASS } from '@/components/dossier/dossierClasses'
import { briefPlainText, briefSummary } from '@/lib/briefView'
import type { components } from '@/types/api'

import BriefRadMark from './BriefRadMark.vue'

const { brief } = defineProps<{ brief: components['schemas']['EditorialBrief'] }>()

const emit = defineEmits<{ edit: [] }>()

// Como en «Siguiente paso»: el aviso dura lo justo para leerlo.
const COPIED_FEEDBACK_MS = 2000
const BRIEF_COPIED = 'Brief copiado, con las URLs de cada punto'
const LINK_COPIED = 'Enlace copiado: abre este mismo brief'
const MOBILE_FILL_CLASS = 'max-sm:grow'

// `legacy`: sin API de portapapeles (HTTP sin TLS, navegadores viejos) copia como siempre.
const briefClipboard = useClipboard({ copiedDuring: COPIED_FEEDBACK_MS, legacy: true })
const linkClipboard = useClipboard({ copiedDuring: COPIED_FEEDBACK_MS, legacy: true })
// El aviso dice la última copia; dura mientras alguna de las dos siga reciente.
const lastCopied = ref<string | null>(null)
const toast = computed(() =>
  briefClipboard.copied.value || linkClipboard.copied.value ? lastCopied.value : null,
)

function copyBrief() {
  lastCopied.value = BRIEF_COPIED
  void briefClipboard.copy(briefPlainText(brief))
}

// Con las cuatro opciones en la URL, el enlace abre este mismo brief sin volver a gastar LLM.
function copyLink() {
  lastCopied.value = LINK_COPIED
  void linkClipboard.copy(window.location.href)
}
</script>

<template>
  <!-- Las acciones del brief, siempre a mano mientras se lee: la cabecera se queda pegada arriba.
       En móvil no, porque con los botones en dos filas taparía media pantalla. -->
  <div
    class="z-10 flex flex-wrap items-center gap-3 rounded-t-card bg-card py-4 pr-5 pl-6 shadow-[0_1px_0_var(--table-line)] sm:sticky sm:top-3"
  >
    <div class="flex min-w-0 flex-[1_1_220px] items-center gap-2.5">
      <BriefRadMark />
      <div class="flex min-w-0 flex-col">
        <h2 class="text-[15px] font-semibold">Brief listo</h2>
        <p class="text-[13px] text-muted-foreground">{{ briefSummary(brief) }}</p>
      </div>
    </div>
    <!-- En móvil los botones se reparten cada fila en lugar de quedar sueltos. -->
    <div class="flex flex-wrap gap-2 max-sm:w-full">
      <button
        type="button"
        :class="[SECONDARY_BUTTON_CLASS, MOBILE_FILL_CLASS]"
        @click="emit('edit')"
      >
        Cambiar enfoque
      </button>
      <button type="button" :class="[SECONDARY_BUTTON_CLASS, MOBILE_FILL_CLASS]" @click="copyLink">
        <Link class="size-4" aria-hidden="true" />
        {{ linkClipboard.copied.value ? 'Enlace copiado' : 'Copiar enlace' }}
      </button>
      <button type="button" :class="[PRIMARY_BUTTON_CLASS, MOBILE_FILL_CLASS]" @click="copyBrief">
        <Copy class="size-4" aria-hidden="true" />
        {{ briefClipboard.copied.value ? 'Brief copiado' : 'Copiar brief' }}
      </button>
    </div>
  </div>

  <!-- Flota sobre la página, así que lleva la sombra flotante (DESIGN.md §5). La región `status`
       existe siempre para que el lector de pantalla anuncie cada aviso al aparecer. -->
  <Teleport to="body">
    <div
      role="status"
      class="pointer-events-none fixed inset-x-0 bottom-7 z-50 flex justify-center px-4"
    >
      <Transition
        enter-active-class="transition-[opacity,translate] duration-[240ms] ease-out motion-reduce:transition-none"
        enter-from-class="translate-y-1 opacity-0"
        leave-active-class="transition-opacity duration-150 ease-out motion-reduce:transition-none"
        leave-to-class="opacity-0"
      >
        <p
          v-if="toast"
          class="flex items-center gap-2.5 rounded-xl bg-primary px-[18px] py-3 text-sm font-semibold text-primary-foreground shadow-float"
        >
          <Check class="size-4 shrink-0 text-signal" :stroke-width="3" aria-hidden="true" />
          {{ toast }}
        </p>
      </Transition>
    </div>
  </Teleport>
</template>
