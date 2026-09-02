<template>
  <PageCard
    title="Relação de Ovinos/lotes"
    subtitle="Lista de lotes e grupos de ovinos"
  >
    <template #top-bar-extra>
      <div class="ovinos-actions">
        <Botao label="Voltar" to="/propriedades" variant="ghost" />
        <Botao
          label="Adicionar Ovinos/Lote"
          to="/propriedades/ovinos/adicionar"
          variant="primary"
        />
      </div>
    </template>

    <Tabela
      :columns="colunas"
      :rows="linhasFormatadas"
      :selectable="false"
      :current-page="paginaAtual"
      @update:current-page="paginaAtual = $event"
      @update:total-pages="totalPaginas = $event"
      @cell-click="handleCellClick"
    />

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
import { computed, ref, watch } from 'vue'
import PageCard from '@/components/ui/PageCard.vue'
import Tabela from '@/components/ui/Tabela.vue'
import Botao from '@/components/ui/Botao.vue'
import Paginacao from '@/components/ui/Paginacao.vue'

const paginaAtual = ref(1)
const totalPaginas = ref(1)

const colunas = [
  { key: 'indice', label: '#', weight: 0.7 },
  { key: 'nomeLote', label: 'Nome lote', weight: 2 },
  { key: 'raca', label: 'Raça', weight: 1.4 },
  { key: 'sistema', label: 'Sistema', weight: 1.4 },
  { key: 'categoria', label: 'Categoria', weight: 1.2 },
  { key: 'fase', label: 'Fase', weight: 1.2 },
  { key: 'pv', label: 'PV', weight: 1 },
  { key: 'gmd', label: 'GMD esperado', weight: 1.3 },
  { key: 'quantidade', label: 'Quantidade', weight: 1 },
  { key: 'idade', label: 'Idade', weight: 1 },
  { key: 'tipoParto', label: 'Tipo de Parto', weight: 1.3 },
  {
    key: 'acoes',
    label: '',
    weight: 1.4,
    render: (row) => `
      <button type="button" class="botao botao-primary btn-row" data-action="editar" data-id="${row.id}">Editar</button>
      <button type="button" class="botao botao-danger btn-row" data-action="remover" data-id="${row.id}">Remover</button>
    `,
  },
]

const linhas = ref(
  Array.from({ length: 10 }, (_, index) => ({
    id: index + 1,
    nomeLote: 'LOTE TESTE 01',
    raca: 'Santa Inês',
    sistema: 'Semi-Confinado',
    categoria: 'Cordeiros',
    fase: 'Crescimento',
    pv: '28 kg',
    gmd: '0,250 kg/dia',
    quantidade: '35',
    idade: '90 dias',
    tipoParto: 'Parto Simples',
  }))
)

const linhasFormatadas = computed(() =>
  linhas.value.map((item, index) => ({
    ...item,
    indice: index + 1,
  }))
)

function handleCellClick({ action }) {
  if (action === 'editar' || action === 'remover') {
    console.log('Ação pendente para ovino:', action)
  }
}

watch(
  linhasFormatadas,
  () => {
    totalPaginas.value = Math.max(1, Math.ceil(linhasFormatadas.value.length / 10))
  },
  { immediate: true }
)
</script>

<style scoped>
.ovinos-actions {
  display: flex;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.btn-row {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 999px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  margin: 0 2px;
  text-decoration: none;
  transition: filter .2s ease;
}

.btn-row:hover {
  filter: brightness(1.08);
}

.botao-primary {
  background: var(--primary-dark);
  color: var(--white);
}

.botao-danger {
  background: #d94d4d;
  color: var(--white);
}
</style>