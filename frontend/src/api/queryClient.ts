import type { VueQueryPluginOptions } from '@tanstack/vue-query'

// La API sirve resultados ya calculados por `analyze`, que cambian como mucho cada pocas horas.
const STALE_TIME_MS = 60_000

export const vueQueryOptions: VueQueryPluginOptions = {
  queryClientConfig: {
    defaultOptions: {
      queries: {
        staleTime: STALE_TIME_MS,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  },
}
