<script lang="ts">
// Lo que puede hacer el primario del panel: uno por panel, nombrado con la acción (DESIGN.md §4).
export const BriefStage = {
  // Sin brief, o con uno de otras opciones: hay que generarlo.
  Idle: 'idle',
  Pending: 'pending',
  Ready: 'ready',
} as const
export type BriefStage = (typeof BriefStage)[keyof typeof BriefStage]
</script>

<script setup lang="ts">
import HoverHint from '@/components/layout/HoverHint.vue'
import InfoTip from '@/components/layout/InfoTip.vue'
import { HELP } from '@/lib/helpText'
import { useClipboard } from '@vueuse/core'

import { recommendationReasonText } from '@/lib/opportunityFormat'

import {
  CARD_CLASS,
  CARD_TITLE_CLASS,
  PRIMARY_BUTTON_CLASS,
  SECONDARY_BUTTON_CLASS,
} from '@/components/dossier/dossierClasses'
import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import {
  BRIEF_FORMAT_LABEL,
  BRIEF_FORMATS,
  BRIEF_GOAL_LABEL,
  BRIEF_GOALS,
  BRIEF_PLATFORM_LABEL,
  BRIEF_PLATFORMS,
  type BriefOptions,
  isAdvisedAgainst,
} from '@/lib/briefView'
import type { components } from '@/types/api'

import BriefOptionGroup from './BriefOptionGroup.vue'

const { opportunity, stage, plainText } = defineProps<{
  opportunity: components['schemas']['Opportunity']
  stage: BriefStage
  // El brief listo para pegar; `null` mientras no hay uno de estas opciones.
  plainText: string | null
}>()

const options = defineModel<BriefOptions>('options', { required: true })

const emit = defineEmits<{ generate: [] }>()

// Como en «Siguiente paso»: el aviso dura lo justo para leerlo.
const COPIED_FEEDBACK_MS = 2000
const ACTION_CLASS = 'min-h-[46px] w-full'

const brief = useClipboard({ copiedDuring: COPIED_FEEDBACK_MS })
const link = useClipboard({ copiedDuring: COPIED_FEEDBACK_MS })

function update<K extends keyof BriefOptions>(key: K, value: BriefOptions[K]) {
  options.value = { ...options.value, [key]: value }
}

function copyBrief() {
  if (plainText !== null) void brief.copy(plainText)
}

// Con las cuatro opciones en la URL, el enlace abre este mismo brief sin volver a gastar LLM.
function copyLink() {
  void link.copy(window.location.href)
}
</script>

<template>
  <section aria-label="Opciones del brief" :class="[CARD_CLASS, 'flex-col gap-5']">
    <h2 :class="[CARD_TITLE_CLASS, 'flex items-center gap-1.5']">
      Brief
      <InfoTip label="el brief" :text="HELP.briefPanel" />
    </h2>

    <!-- La API genera el brief igual y lo devuelve con la recomendación: la UI no lo esconde,
         pero avisa antes de que se pida. -->
    <div
      v-if="isAdvisedAgainst(opportunity.recommendation)"
      class="flex flex-col items-start gap-2 rounded-tile bg-sunken px-4 py-3.5"
    >
      <RecommendationChip :recommendation="opportunity.recommendation" size="sm" />
      <p v-if="recommendationReasonText(opportunity)" class="text-sm text-ink-soft">
        {{ recommendationReasonText(opportunity) }}
      </p>
    </div>

    <BriefOptionGroup
      label="Plataforma"
      :help="HELP.briefPlatform"
      :options="BRIEF_PLATFORMS"
      :labels="BRIEF_PLATFORM_LABEL"
      :model-value="options.platform"
      @update:model-value="update('platform', $event)"
    />
    <BriefOptionGroup
      label="Objetivo"
      :help="HELP.briefGoal"
      :options="BRIEF_GOALS"
      :labels="BRIEF_GOAL_LABEL"
      :model-value="options.goal"
      @update:model-value="update('goal', $event)"
    />
    <BriefOptionGroup
      label="Formato"
      :help="HELP.briefFormat"
      :options="BRIEF_FORMATS"
      :labels="BRIEF_FORMAT_LABEL"
      :model-value="options.format"
      @update:model-value="update('format', $event)"
    />

    <div class="flex flex-col gap-2 pt-1">
      <HoverHint v-if="stage === BriefStage.Ready" :text="HELP.copyBrief">
        <button
          type="button"
          aria-live="polite"
          :class="[PRIMARY_BUTTON_CLASS, ACTION_CLASS]"
          @click="copyBrief"
        >
          {{ brief.copied.value ? 'Brief copiado' : 'Copiar brief' }}
        </button>
      </HoverHint>
      <button
        v-else
        type="button"
        :disabled="stage === BriefStage.Pending"
        :class="[
          PRIMARY_BUTTON_CLASS,
          ACTION_CLASS,
          'disabled:pointer-events-none disabled:opacity-50',
        ]"
        @click="emit('generate')"
      >
        Generar brief
      </button>
      <HoverHint v-if="stage === BriefStage.Ready" :text="HELP.copyLink">
        <button
          type="button"
          aria-live="polite"
          :class="[SECONDARY_BUTTON_CLASS, ACTION_CLASS]"
          @click="copyLink"
        >
          {{ link.copied.value ? 'Enlace copiado' : 'Copiar enlace' }}
        </button>
      </HoverHint>
    </div>
  </section>
</template>
