<template>
  <PageCard variant="admin" header-theme="dark">
    <template #top-tabs>
      <TabsHeader v-model="activeTab" :tabs="tabs" />
    </template>

    <div class="admin-dashboard">
      <div class="admin-dashboard__main">
        <h2 class="section-title">KPIs do Sistema</h2>

        <div class="kpi-grid">
          <div class="kpi-card" v-for="kpi in kpis" :key="kpi.label">
            <span class="kpi-label">{{ kpi.label }}</span>
            <strong class="kpi-value">{{ kpi.value }}</strong>
            <span class="kpi-delta">{{ kpi.delta }}</span>
          </div>
        </div>

        <h2 class="section-title">Últimos Usuários Cadastrados</h2>

        <div class="usuarios-table">
          <div class="usuarios-table__header">
            <span>Nome</span>
            <span>E-mail</span>
            <span>Data cadastro</span>
            <span>Status</span>
          </div>

          <div
            v-for="usuario in ultimosUsuarios"
            :key="usuario.id"
            class="usuarios-table__row"
          >
            <span>{{ usuario.nome }}</span>
            <span>{{ usuario.email }}</span>
            <span>{{ usuario.dataCadastro }}</span>
            <span class="status">
              <span class="status-dot" :class="statusClass(usuario.status)" />
              {{ usuario.status }}
            </span>
          </div>
        </div>
      </div>

      <div class="admin-dashboard__side">
        <h2 class="section-title">Alertas Gerais</h2>

        <ul class="alertas-box">
          <li
            v-for="alerta in alertas"
            :key="alerta.id"
            class="alerta-item"
          >
            <span class="alerta-dot" :style="{ background: alerta.cor }" />
            {{ alerta.texto }}
          </li>
        </ul>
      </div>
    </div>
  </PageCard>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import PageCard from '@/components/ui/PageCard.vue'
import TabsHeader from '@/components/ui/TabsHeader.vue'
import { adminAPI } from '@/services/api'

const router = useRouter()
const activeTab = ref('dashboard')

const tabs = [
  { key: 'dashboard', label: 'Dashboard Principal' },
  { key: 'usuarios', label: 'Gestão De Usuários' },
  { key: 'permissoes', label: 'Permissões' },
  { key: 'logs', label: 'Logs de Auditoria' },
  { key: 'configuracoes', label: 'Configurações do Sistema' },
]

const rotaPorAba = {
  dashboard: 'AdminDashboard',
  usuarios: 'AdminUsuarios',
  permissoes: 'AdminPermissoes',
  logs: 'AdminLogs',
  configuracoes: 'AdminConfiguracoes',
}

watch(activeTab, (value) => {
  const rota = rotaPorAba[value]
  if (rota) {
    router.push({ name: rota })
  }
})

const kpis = ref([
  { key: 'usuarios', label: 'Total de Usuários', value: '0', delta: '' },
  { key: 'ativos', label: 'Usuários Ativos', value: '0', delta: '' },
  { key: 'propriedades', label: 'Propriedades', value: '0', delta: '' },
  { key: 'formulacoes', label: 'Formulações', value: '0', delta: '' },
])

const ultimosUsuarios = ref([])
const alertas = ref([])

function statusClass(status) {
  if (status === 'Ativo') return 'status-ok'
  if (status === 'Pendente') return 'status-pending'
  return 'status-inativo'
}

async function carregarDashboard() {
  try {
    const { data } = await adminAPI.obterDashboard()

    kpis.value = [
      { key: 'usuarios', label: 'Total de Usuários', value: data.totalUsuarios, delta: data.deltaUsuarios },
      { key: 'ativos', label: 'Usuários Ativos', value: data.usuariosAtivos, delta: data.deltaAtivos },
      { key: 'propriedades', label: 'Propriedades', value: data.totalPropriedades, delta: data.deltaPropriedades },
      { key: 'formulacoes', label: 'Formulações', value: data.totalFormulacoes, delta: data.deltaFormulacoes },
    ]

    ultimosUsuarios.value = data.ultimosUsuarios || []
    alertas.value = data.alertas || []
  } catch (error) {
    console.error('Erro ao carregar dashboard administrativo:', error)
    kpis.value = kpis.value.map((kpi) => ({ ...kpi, value: '-', delta: '' }))
    ultimosUsuarios.value = []
    alertas.value = []
  }
}

onMounted(carregarDashboard)
</script>

<style scoped>
.admin-dashboard {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: var(--space-lg);
  align-items: start;
}

.admin-dashboard__main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.admin-dashboard__side {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.section-title {
  margin: 0 0 var(--space-sm);

  font-size: 1.2rem;
  font-weight: 700;

  color: var(--text);
}

/* KPIs */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
}

.kpi-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;

  padding: var(--space-md) var(--space-sm);

  background: var(--primary-dark);
  border-radius: var(--radius-lg);

  text-align: center;
}

.kpi-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .4px;
  text-transform: uppercase;

  color: rgba(255,255,255,.85);
}

.kpi-value {
  font-size: 2rem;
  font-weight: 700;

  color: #fff;
}

.kpi-delta {
  font-size: 12px;

  color: rgba(255,255,255,.75);
}

/* Últimos usuários */
.usuarios-table {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.usuarios-table__header,
.usuarios-table__row {
  display: grid;
  grid-template-columns: 1.2fr 1.6fr 1fr .8fr;
  align-items: center;
  gap: var(--space-sm);
}

.usuarios-table__header {
  padding: 0 var(--space-md);

  font-size: 13px;
  font-weight: 600;

  color: var(--text);
}

.usuarios-table__row {
  padding: 12px var(--space-md);

  background: var(--primary-dark);
  border-radius: var(--radius-md);

  font-size: 13px;

  color: #fff;
}

.status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-ok {
  background: #4caf50;
}

.status-pending {
  background: #f2c94c;
}

.status-inativo {
  background: #d94d4d;
}

/* Alertas */
.alertas-box {
  list-style: none;
  margin: 0;
  padding: var(--space-md);

  display: flex;
  flex-direction: column;
  gap: 12px;

  background: var(--primary-dark);
  border-radius: var(--radius-lg);
}

.alerta-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;

  font-size: 13px;
  line-height: 1.4;

  color: #fff;
}

.alerta-dot {
  width: 9px;
  height: 9px;
  margin-top: 4px;
  border-radius: 50%;
  flex-shrink: 0;
}

@media (max-width: 1200px) {
  .admin-dashboard {
    grid-template-columns: 1fr;
  }

  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .kpi-grid {
    grid-template-columns: 1fr;
  }

  .usuarios-table__header,
  .usuarios-table__row {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}
</style>