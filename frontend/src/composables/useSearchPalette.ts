import { ref } from 'vue'

// Una sola paleta en toda la app: la abre ⌘K desde la cabecera y, en Crear, «Buscar otro tema».
const open = ref(false)

export function useSearchPalette() {
  return { open }
}
