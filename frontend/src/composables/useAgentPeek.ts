import { createGlobalState } from '@vueuse/core'
import { computed, shallowRef } from 'vue'

// El tema citado que la persona está mirando en la barra de Rad (DESIGN.md §4, «Vistazo»). La
// barra vive en App.vue y la vista que lo resalta, dentro del router: por eso es un estado
// compartido. No va en la URL ni cambia la selección: es un hover, no una elección.
export const useAgentPeek = createGlobalState(() => {
  const peeked = shallowRef<string | null>(null)

  function peek(id: string | null) {
    peeked.value = id
  }

  return { peekedId: computed(() => peeked.value), peek }
})
