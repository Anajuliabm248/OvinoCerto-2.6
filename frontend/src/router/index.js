import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../pages/geral/Home.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('../pages/geral/Home.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/frontpage',
    name: 'FrontPage',
    component: () => import('../pages/geral/FrontPage.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/login/Login.vue'),
  },
  {
    path: '/cadastro',
    name: 'Cadastro',
    component: () => import('../pages/login/Cadastro.vue'),
  },
  {
    path: '/recuperar-senha',
    name: 'RecuperacaoSenha',
    component: () => import('../pages/login/RecuperacaoSenha.vue'),
  },
  {
    path: '/conta',
    name: 'Conta',
    component: () => import('../pages/login/Perfil.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/formulacoes/dashboard',
    name: 'FormulacaoDashboard',
    component: () => import('../pages/formulacao/FormulacaoDashboard.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/formulacoes/dashboard/dados',
    name: 'FormulacaoDashboardDados',
    component: () => import('../pages/formulacao/FormulacaoDashboardDados.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/formulacoes/ajustes-dieta',
    name: 'FormulacaoAjustesDieta',
    component: () => import('../pages/formulacao/FormulacaoAjustesDieta.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/formulacoes/custos',
    name: 'FormulacaoCustos',
    component: () => import('../pages/formulacao/FormulacaoCustos.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/formulacoes/ajustes-alimentacao',
    name: 'FormulacaoAjustesAlimentacao',
    component: () => import('../pages/formulacao/FormulacaoAjustesAlimentacao.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/formulacoes/observacoes',
    name: 'FormulacaoObservacoes',
    component: () => import('../pages/formulacao/FormulacaoObservacoes.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/formulacoes/relatorio',
    name: 'FormulacaoRelatorio',
    component: () => import('../pages/formulacao/FormulacaoRelatorio.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/formulacoes/exigencias',
    name: 'FormulacaoExigencias',
    component: () => import('../pages/formulacao/FormulacaoExigencias.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/formulacoes/ingredientes',
    name: 'FormulacaoIngrediente',
    component: () => import('../pages/formulacao/FormulacaoIngrediente.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/formulacoes/propriedades',
    name: 'FormulacaoPropriedade',
    component: () => import('../pages/formulacao/FormulacaoPropriedade.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/exigencias-nutricionais',
    name: 'ExigenciasNutricionais',
    component: () => import('../pages/exigencias/BancoExigencias.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/propriedades',
    name: 'Propriedades',
    component: () => import('../pages/propriedade/BancoPropriedades.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/propriedades/adicionar',
    name: 'NovaPropriedade',
    component: () => import('../pages/propriedade/AdicionarPropriedade.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/ingredientes',
    name: 'Ingredientes',
    component: () => import('../pages/ingrediente/BancoIngredientes.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/ingredientes/adicionar',
    name: 'AdicionarIngrediente',
    component: () => import('../pages/ingrediente/AdicionarIngrediente.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/propriedades/ovinos',
    name: 'Ovinos',
    component: () => import('../pages/ovinos/BancoOvinos.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/propriedades/ovinos/adicionar',
    name: 'AdicionarOvino',
    component: () => import('../pages/ovinos/AdicionarOvinos.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/propriedades/:id/lotes',
    name: 'Lotes',
    component: () => import('../pages/ovinos/BancoOvinos.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: () => import('../pages/admin/AdminDashboard.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/admin/usuarios',
    name: 'AdminUsuarios',
    component: () => import('../pages/admin/AdminUsuarios.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/admin/configuracoes',
    name: 'AdminConfiguracoes',
    component: () => import('../pages/admin/AdminConfiguracao.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/admin/logs',
    name: 'AdminLogs',
    component: () => import('../pages/admin/AdminLogs.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/admin/permissoes',
    name: 'AdminPermissoes',
    component: () => import('../pages/admin/AdminPermissoes.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Guard de rotas - verificar autenticação e papel do usuário
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth)
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin)
  const isAdminRoute = to.matched.some((record) => record.meta.role === 'admin')

  if (authStore.token && !authStore.user) {
    try {
      await authStore.fetchProfile()
    } catch (error) {
      authStore.logout()
    }
  }

  if (requiresAuth && !authStore.isAuthenticated) {
    next('/login')
    return
  }

  if (isAdminRoute && !authStore.isAdmin) {
    next('/home')
    return
  }

  if (requiresAdmin && !authStore.isAdmin) {
    next('/home')
    return
  }

  if (to.meta.requireUserManagement && !authStore.canManageUsers) {
    next('/home')
    return
  }

  if (to.path === '/login' && authStore.isAuthenticated) {
    next('/home')
    return
  }

  next()
})

export default router
