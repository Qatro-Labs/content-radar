import { createRouter, createWebHistory } from 'vue-router'

import DiscoverView from '@/views/DiscoverView.vue'

export const RouteName = {
  Discover: 'discover',
  Explore: 'explore',
  Dossier: 'dossier',
  Create: 'create',
} as const

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: RouteName.Discover, component: DiscoverView },
    {
      path: '/explore',
      name: RouteName.Explore,
      component: () => import('@/views/ExploreView.vue'),
    },
    {
      path: '/explore/:id',
      name: RouteName.Dossier,
      component: () => import('@/views/DossierView.vue'),
    },
    {
      path: '/create',
      name: RouteName.Create,
      component: () => import('@/views/CreateView.vue'),
    },
    { path: '/:pathMatch(.*)*', redirect: { name: RouteName.Discover } },
  ],
})
