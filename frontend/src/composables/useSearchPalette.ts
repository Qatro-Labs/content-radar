import { ref } from 'vue'

// Una sola paleta en toda la app, la de la cabecera (⌘K): el estado vive fuera del componente
// para que cualquier vista pueda abrirla. Desde Crear, elegir un tema abre su brief
// (`topicDestination`).
const open = ref(false)

export function useSearchPalette() {
  return { open }
}
