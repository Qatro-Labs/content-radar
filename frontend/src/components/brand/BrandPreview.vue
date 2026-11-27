<script setup lang="ts">
import { computed } from 'vue'

import type { BrandPreviewModel } from '@/lib/brandProfile'
import { HOOK_MISSING } from '@/lib/briefView'

// La vista previa no llama al LLM (R4): pone el tema y el gancho del último brief del equipo, o un
// tema de ejemplo marcado como tal, junto a lo que dice el borrador ahora mismo.
const props = defineProps<{ preview: BrandPreviewModel; editable: boolean }>()

const EXAMPLE_HOOK = 'Cada brief trae un gancho para su tema, escrito en este tono.'
const SECTION_LABEL_CLASS = 'text-xs font-semibold text-on-ink-muted'

const title = computed(() =>
  props.editable ? 'ASÍ SE VERÍA TU PRÓXIMO BRIEF' : 'ASÍ SALEN SUS BRIEFS',
)
const sourceLabel = computed(() =>
  props.preview.isExample ? 'ejemplo' : 'último brief del equipo',
)
const hook = computed(() => {
  if (props.preview.hook !== null) return props.preview.hook
  return props.preview.isExample ? EXAMPLE_HOOK : HOOK_MISSING
})
const toneLabel = computed(() => props.preview.tone.join(', ').toLocaleUpperCase('es'))
</script>

<template>
  <aside
    aria-label="Vista previa del brief"
    class="flex flex-[1_1_380px] flex-col gap-3.5 rounded-[24px] bg-primary p-6 text-primary-foreground lg:sticky lg:top-4"
  >
    <div class="flex flex-wrap items-center justify-between gap-2">
      <span class="text-[13px] font-semibold text-signal">{{ title }}</span>
      <span class="text-xs text-on-ink-muted">{{ sourceLabel }}</span>
    </div>
    <p class="font-display text-2xl leading-[1.15] font-semibold tracking-[-0.02em]">
      {{ preview.topic }}
    </p>

    <div class="flex flex-col gap-1 rounded-tile bg-ink-read p-3.5">
      <span :class="SECTION_LABEL_CLASS">GANCHO · TONO {{ toneLabel }}</span>
      <span class="text-[17px] leading-[1.4]">{{ hook }}</span>
    </div>

    <div class="flex flex-col gap-1">
      <span :class="SECTION_LABEL_CLASS">PARA QUIÉN</span>
      <span class="text-[15px] leading-[1.45]">{{ preview.audience }}</span>
      <span class="text-sm text-on-ink-muted">En {{ preview.region }}.</span>
    </div>

    <div class="flex flex-col gap-1">
      <span :class="SECTION_LABEL_CLASS">CIERRE</span>
      <span class="text-[15px] leading-[1.45]">
        {{ preview.callToAction ? `Invita a: ${preview.callToAction}.` : 'Sin cierre definido.' }}
      </span>
    </div>

    <div class="flex flex-col gap-1 border-t border-ink-soft pt-3">
      <span :class="SECTION_LABEL_CLASS">EL BRIEF EVITA</span>
      <span class="text-sm leading-[1.45] text-on-ink-muted">
        {{ preview.neverSay ?? 'Nada definido.' }}
      </span>
    </div>

    <p class="text-[13px] text-on-ink-muted">{{ preview.weeklyLine }}</p>
  </aside>
</template>
