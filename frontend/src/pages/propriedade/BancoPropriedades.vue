<template>
  <PageCard
    title="Relação de Propriedades"
    subtitle="Lista de propriedades cadastradas"
  >
    <template #top-bar-extra>
      <div class="properties-actions">
        <Botao label="Ver Ovinos/lotes" to="/propriedades/ovinos" variant="primary" type="button" />
        <Botao
          label="Adicionar Propriedade"
          to="/propriedades/adicionar"
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
import { computed, onMounted, ref, watch } from 'vue'
import PageCard from '@/components/ui/PageCard.vue'
import Tabela from '@/components/ui/Tabela.vue'
import Botao from '@/components/ui/Botao.vue'
import Paginacao from '@/components/ui/Paginacao.vue'
import { propriedadesAPI } from '@/services/api'

const paginaAtual = ref(1)
const totalPaginas = ref(1)
const linhas = ref([])

const colunas = [
  { key: 'indice', label: '#', weight: 0.7 },
  { key: 'nome', label: 'Nome', weight: 2 },
  { key: 'proprietario', label: 'Proprietário', weight: 1.8 },
  { key: 'telefone', label: 'Telefone', weight: 1.2 },
  { key: 'uf', label: 'UF', weight: 1 },
  { key: 'cidade', label: 'Cidade', weight: 1.4 },
  { key: 'localidade', label: 'Localidade', weight: 1.4 },
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

const linhasFormatadas = computed(() =>
  linhas.value.map((item, index) => ({
    ...item,
    indice: index + 1,
  }))
)

function handleCellClick({ action }) {
  if (action === 'editar' || action === 'remover') {
    console.log('Ação pendente para propriedade:', action)
  }
}

const carregarPropriedades = async () => {
  try {
    const response = await propriedadesAPI.listar({ page: 1, page_size: 100 })
    const dados = response.data.results || response.data || []
    linhas.value = Array.isArray(dados) ? dados : []
  } catch (error) {
    console.error('Erro ao carregar propriedades:', error)
    linhas.value = []
  }
}

watch(
  linhasFormatadas,
  () => {
    totalPaginas.value = Math.max(1, Math.ceil(linhasFormatadas.value.length / 10))
  },
  { immediate: true }
)

onMounted(carregarPropriedades)
</script>

<style scoped>
.properties-actions {
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