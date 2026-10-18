// Aparte del router: el router importa las vistas, y lo que las vistas usan (el agente, sus
// objetivos) necesita los nombres de ruta sin crear un ciclo de imports.
export const RouteName = {
  Discover: 'discover',
  Explore: 'explore',
  Dossier: 'dossier',
  Create: 'create',
  Login: 'login',
} as const
