<template>
  <PageCard
    title="Banco de Ingredientes"
    subtitle="Composição Bromatológica e Custos dos Ingredientes"
  >
    <template #top-tabs>
      <TabsHeader v-model="activeTab" :tabs="tabs" />
    </template>

    <template #top-bar-extra>
      <Botao label="Adicionar Ingrediente" to="/ingredientes/adicionar" variant="primary" />
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
import { ref, computed, watch, onMounted } from 'vue'
import PageCard from '@/components/ui/PageCard.vue'
import TabsHeader from '@/components/ui/TabsHeader.vue'
import Tabela from '@/components/ui/Tabela.vue'
import Botao from '@/components/ui/Botao.vue'
import Paginacao from '@/components/ui/Paginacao.vue'
import { ingredientesAPI } from '@/services/api'

const tabs = [
  { key: 'sistema', label: 'Ingredientes do Sistema' },
  { key: 'usuario', label: 'Ingredientes do Usuário' },
]

const activeTab = ref('usuario')
const paginaAtual = ref(1)
const totalPaginas = ref(1)
const linhas = ref([])

const colunas = [
  { key: 'indice', label: '#', weight: 0.7 },
  { key: 'classificacao_display', label: 'Classificação', weight: 1.3 },
  { key: 'tipo_display', label: 'Tipo', weight: 1.5 },
  { key: 'nome', label: 'Ingrediente', weight: 1.8 },
  { key: 'ms', label: 'MS(%)', weight: 1 },
  { key: 'pb', label: 'PB(%)', weight: 1 },
  { key: 'ndt', label: 'NDT(%)', weight: 1 },
  { key: 'fdn', label: 'FDN(%)', weight: 1 },
  { key: 'ee', label: 'EE(%)', weight: 1 },
  { key: 'ca', label: 'C(%)', weight: 1 },
  { key: 'p', label: 'P(%)', weight: 1 },
  { key: 'custo', label: 'R$ (kg/MN)', weight: 1.2 },
  {
    key: 'acoes',
    label: '',
    weight: 1.4,
    render: (row) => {
      const botoes = [
        `<button type="button" class="btn-row btn-editar" data-action="editar" data-id="${row.id}">Editar</button>`,
      ]

      if (!row.fonte_valadares) {
        botoes.push(`<button type="button" class="btn-row btn-remover" data-action="remover" data-id="${row.id}">Remover</button>`)
      }

      return botoes.join('')
    },
  },
]

const linhasFormatadas = computed(() =>
  linhas.value.map((item, index) => {
    const preco = item.preco_kg_mn ?? item.custo_kg ?? 0
    return {
      ...item,
      indice: index + 1,
      ms: Number(item.ms ?? 0).toFixed(2),
      pb: Number(item.pb ?? 0).toFixed(2),
      ndt: Number(item.ndt ?? 0).toFixed(2),
      fdn: Number(item.fdn ?? 0).toFixed(2),
      ee: Number(item.ee ?? 0).toFixed(2),
      ca: Number(item.ca ?? 0).toFixed(2),
      p: Number(item.p ?? 0).toFixed(2),
      custo: `R$ ${Number(preco).toFixed(2)}`,
    }
  })
)

function handleCellClick({ action, row }) {
  if (action === 'editar') {
    console.log('Editar ingrediente', row.id)
    return
  }

  if (action === 'remover') {
    removerIngrediente(row)
  }
}

const carregarIngredientes = async () => {
  try {
    let pagina = 1
    const registros = []
    const valadares = activeTab.value === 'sistema' ? 'true' : 'false'

    while (true) {
      const response = await ingredientesAPI.listar({
        valadares,
        page: pagina,
        page_size: 100,
      })

      const dados = response.data.results || response.data || []
      if (!Array.isArray(dados) || dados.length === 0) {
        break
      }

      registros.push(...dados)

      if (!response.data.next || dados.length < 100) {
        break
      }

      pagina += 1
    }

    linhas.value = registros
  } catch (error) {
    console.error('Erro ao carregar ingredientes:', error)
    linhas.value = []
    totalPaginas.value = 1
  }
}

async function removerIngrediente(item) {
  if (!item || item.fonte_valadares) return

  const ok = window.confirm(`Remover o ingrediente "${item.nome}"?`)
  if (!ok) return

  try {
    await ingredientesAPI.deletar(item.id)
    await carregarIngredientes()
  } catch (error) {
    console.error('Erro ao remover ingrediente:', error)
    alert('Não foi possível remover o ingrediente.')
  }
}

watch(activeTab, () => {
  paginaAtual.value = 1
  carregarIngredientes()
})

watch(
  linhasFormatadas,
  () => {
    totalPaginas.value = Math.max(1, Math.ceil(linhasFormatadas.value.length / 10))
  },
  { immediate: true }
)

onMounted(carregarIngredientes)
</script>

<style scoped>
.btn-row {
  border: none;
  border-radius: 999px;
  padding: 7px 10px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  margin: 0 2px;
}

.btn-remover {
  background: #d94d4d;
  color: #fff;
}

.btn-editar {
  background: #5f7317;
  color: #fff;
}
</style>
