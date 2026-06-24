import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../pages/Home.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/Login.vue'),
  },
  {
    path: '/cadastro',
    name: 'Cadastro',
    component: () => import('../pages/Cadastro.vue'),
  },
  {
    path: '/recuperar-senha',
    name: 'RecuperacaoSenha',
    component: () => import('../pages/RecuperacaoSenha.vue'),
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../pages/Dashboard.vue'),
  },
  {
    path: '/propriedades',
    name: 'Propriedades',
    component: () => import('../pages/Propriedades.vue'),
  },
  {
    path: '/ingredientes',
    name: 'Ingredientes',
    component: () => import('../pages/BancoIngredientes.vue'),
  },
  {
    path: '/exigencias',
    name: 'Exigencias',
    component: () => import('../pages/Exigencias.vue'),
  },
  {
    path: '/propriedades/:id/lotes',
    name: 'Lotes',
    component: () => import('../pages/Lotes.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Guard de rotas - verificar autenticação
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth)

  if (requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
