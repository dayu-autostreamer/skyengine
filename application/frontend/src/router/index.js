import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import FactoryView from '../views/FactoryView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { title: '首页' }
    },
    {
      path: '/factory',
      name: 'factory',
      component: FactoryView,
      meta: { title: '工厂管理系统' }
    },
  ],
})

export default router
