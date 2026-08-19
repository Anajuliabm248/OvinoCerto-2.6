<template>
  <PageCard
    title="Banco de Ingredientes"
    subtitle="Composição Bromatológica e Custos dos Ingredientes"
  >
    <template #top-tabs>
      <TabsHeader
        v-model="activeTab"
        :tabs="tabs"
      />
    </template>

    <template #top-bar-extra>
      <Botao
        label="Adicionar Ingrediente"
        to="/ingredientes/adicionar"
        variant="primary"
      />
    </template>

    <Tabela
      :columns="colunas"
      :rows="linhas"
      :selectable="false"
      :current-page="paginaAtual"
      @update:current-page="paginaAtual = $event"
      @update:total-pages="totalPaginas = $event"
    />

    <template #actions>
      <Botao label="Salvar Mudanças" type="button" />
    </template>

    <template #pagination>
      <Paginacao
        :total-pages="totalPaginas"
        :current-page="paginaAtual"
        @update:current-page="paginaAtual = $event"
      />
    </template>
  </PageCard>
</template>

<script setup>
import { ref } from 'vue'
import PageCard from '@/components/ui/PageCard.vue'
import TabsHeader from '@/components/ui/TabsHeader.vue'
import Tabela from '@/components/ui/Tabela.vue'
import Botao from '@/components/ui/Botao.vue'
import Paginacao from '@/components/ui/Paginacao.vue'

const tabs = [
  { key: 'sistema', label: 'Ingredientes do Sistema' },
  { key: 'usuario', label: 'Ingredientes do Usuário' },
]

const activeTab = ref('sistema')
const paginaAtual = ref(1)
const totalPaginas = ref(1)

const colunas = [
  { key: 'classificacao', label: 'Classificação', weight: 1.3 },
  { key: 'tipo', label: 'Tipo', weight: 1.5 },
  { key: 'ingrediente', label: 'Ingrediente', weight: 1.8 },
  { key: 'ms', label: 'MS(%)', weight: 1 },
  { key: 'pb', label: 'PB(%)', weight: 1 },
  { key: 'ndt', label: 'NDT(%)', weight: 1 },
  { key: 'fdn', label: 'FDN(%)', weight: 1 },
  { key: 'ee', label: 'EE(%)', weight: 1 },
  { key: 'ca', label: 'C(%)', weight: 1 },
  { key: 'p', label: 'P(%)', weight: 1 },
  { key: 'custo', label: 'R$ (kg/MN)', weight: 1.2 },
]

const linhas = ref(
  Array.from({ length: 10 }, (_, index) => ({
    id: index + 1,
    classificacao: 'Volumoso',
    tipo: 'Forragens Secas',
    ingrediente: 'Alfafa Feno',
    ms: '89.30',
    pb: '18.49',
    ndt: '58.51',
    fdn: '46.78',
    ee: '2.52',
    ca: '1.32',
    p: '1.23',
    custo: 'R$ 5,00',
  }))
)
</script>

<style scoped>
.btn-action {
  border: none;
  background: var(--primary-dark);
  color: var(--white);
  padding: 10px 20px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 13px;
}

@media (max-width: 768px) {
  .btn-action {
    width: 100%;
    justify-content: center;
  }
}
</style>