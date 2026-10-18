import type { LocationQueryValue, NavigationGuard } from 'vue-router'

import { RouteName } from './routeNames'

export const REDIRECT_PARAM = 'redirect'

// Solo rutas de esta app: `//otro.sitio` o una URL absoluta en `?redirect=` llevarían fuera tras
// iniciar sesión.
export function safeRedirect(
  value: LocationQueryValue | LocationQueryValue[] | undefined,
): string | null {
  if (typeof value !== 'string') return null
  return value.startsWith('/') && !value.startsWith('//') ? value : null
}

export function createAuthGuard(hasSession: () => Promise<boolean>): NavigationGuard {
  return async (to) => {
    if (to.name === RouteName.Login) return true
    if (await hasSession()) return true
    return { name: RouteName.Login, query: { [REDIRECT_PARAM]: to.fullPath } }
  }
}
