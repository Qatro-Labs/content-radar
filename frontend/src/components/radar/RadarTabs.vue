<script lang="ts">
import type { RadarTab } from '@/lib/radarQuery'

export const TAB_PANEL_ID = 'radar-tab-panel'
export const tabId = (tab: RadarTab) => `radar-tab-${tab}`

// Las pestañas van en la cabecera de cada tarjeta, así que al cambiar se monta otra copia: esta
// marca le pasa el foco para que el teclado no se pierda en el `body`.
let focusOnMount = false
</script>

<script setup lang="ts">
import { List, Radar } from '@lucide/vue'
import { onMounted, useTemplateRef } from 'vue'

import { useRadarQuery } from '@/composables/useRadarQuery'
import { RADAR_TABS } from '@/lib/radarQuery'

const { query, update } = useRadarQuery()

// Radar y ranking pesan lo mismo: cada pestaña dice qué enseña, no solo cómo se llama.
const TABS: Record<RadarTab, { label: string; caption: string; icon: typeof Radar }> = {
  radar: { label: 'Radar', caption: 'Crecimiento frente a encaje', icon: Radar },
  ranking: { label: 'Ranking', caption: 'Ordenados por oportunidad', icon: List },
}

const buttons = useTemplateRef<HTMLButtonElement[]>('buttons')

onMounted(() => {
  if (!focusOnMount) return
  focusOnMount = false
  buttons.value?.[RADAR_TABS.indexOf(query.value.tab)]?.focus({ preventScroll: true })
})

function choose(tab: RadarTab) {
  if (tab === query.value.tab) return
  focusOnMount = true
  void update({ tab })
}

// Patrón de pestañas de WAI-ARIA: las flechas eligen la pestaña de al lado.
function move(from: RadarTab, step: number) {
  const index = (RADAR_TABS.indexOf(from) + step + RADAR_TABS.length) % RADAR_TABS.length
  choose(RADAR_TABS[index]!)
}
</script>

<template>
  <div
    role="tablist"
    aria-label="Cómo ver los temas"
    class="flex gap-1 rounded-[14px] bg-secondary p-1"
  >
    <button
      v-for="tab in RADAR_TABS"
      :id="tabId(tab)"
      ref="buttons"
      :key="tab"
      type="button"
      role="tab"
      :aria-selected="query.tab === tab"
      :aria-controls="TAB_PANEL_ID"
      :tabindex="query.tab === tab ? 0 : -1"
      class="flex min-h-[56px] items-center gap-3 rounded-[11px] px-4 text-left transition-colors duration-150 ease-out sm:min-w-[220px]"
      :class="
        query.tab === tab ? 'bg-card text-foreground' : 'text-ink-soft hover:bg-secondary-hover'
      "
      @click="choose(tab)"
      @keydown.right.prevent="move(tab, 1)"
      @keydown.left.prevent="move(tab, -1)"
    >
      <component :is="TABS[tab].icon" class="size-5 shrink-0" aria-hidden="true" />
      <span class="flex flex-col">
        <span class="font-display text-lg leading-tight font-semibold tracking-[-0.01em]">
          {{ TABS[tab].label }}
        </span>
        <span class="text-[12.5px] text-muted-foreground">{{ TABS[tab].caption }}</span>
      </span>
    </button>
  </div>
</template>
