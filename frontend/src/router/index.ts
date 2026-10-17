import { createRouter, createWebHistory } from 'vue-router'

import DiscoverView from '@/views/DiscoverView.vue'

export const RouteName = {
  Discover: 'discover',
  Explore: 'explore',
  Create: 'create',
} as const

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: RouteName.Discover, component: DiscoverView },
    {
      path: '/explore/:id?',
      name: RouteName.Explore,
      component: () => import('@/views/ExploreView.vue'),
    },
    {
      path: '/create',
      name: RouteName.Create,
      component: () => import('@/views/CreateView.vue'),
    },
    { path: '/:pathMatch(.*)*', redirect: { name: RouteName.Discover } },
  ],
})
