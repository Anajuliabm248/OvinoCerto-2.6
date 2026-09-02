<template>
  <PageCard
    title="Exigências Nutricionais"
    subtitle="Descrição"
  >
    <template #top-bar-extra>
      <button class="btn-action" type="button">
        Adicionar Exigência
      </button>
    </template>

    <Tabela
      :columns="colunas"
      :rows="linhasComIndice"
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
import { ref, onMounted, computed } from 'vue'
import PageCard from '@/components/ui/PageCard.vue'
import Tabela from '@/components/ui/Tabela.vue'
import Botao from '@/components/ui/Botao.vue'
import Paginacao from '@/components/ui/Paginacao.vue'
import { exigenciasAPI } from '@/services/api'

const paginaAtual = ref(1)
const totalPaginas = ref(1)

const colunas = [
  { key: 'indice', label: '#', weight: 1 },
  { key: 'categoria_display', label: 'Categoria', wrap: true, weight: 2 },
  { key: 'fase_display', label: 'Fase', weight: 1.8 },
  { key: 'pv_kg', label: 'PV (kg)', weight: 1 },
  { key: 'tipo_parto_display', label: 'Tipo Parto', weight: 1.2 },
  { key: 'pv_nascer_kg', label: 'PV Nascença (kg)', weight: 1.6 },
  { key: 'producao_leite_kg_dia', label: 'Prod. Leite (kg/dia)', weight: 1.6 },
  { key: 'gmd_kg', label: 'GMD (kg)', weight: 1 },
  { key: 'pv_percentual', label: 'PV (%)', weight: 1 },
  { key: 'cms_kg', label: 'CMS (kg)', weight: 1 },
  { key: 'pb_g', label: 'PB (g)', weight: 1 },
  { key: 'pb_percentual', label: 'PB (%)', weight: 1.3 },
  { key: 'ndt_kg', label: 'NDT (kg)', weight: 1 },
  { key: 'ndt_percentual', label: 'NDT (%)', weight: 1.3 },
  { key: 'fdn_kg', label: 'FDN (kg)', weight: 1.3 },
  { key: 'fdn_percentual', label: 'FDN (%)', weight: 1 },
  { key: 'ee_kg', label: 'EE (kg)', weight: 1 },
  { key: 'ee_percentual', label: 'EE (%)', weight: 1 },
  { key: 'ca_g', label: 'Ca (g)', weight: 1 },
  { key: 'ca_percentual', label: 'Ca (%)', weight: 1.3 },
  { key: 'p_g', label: 'P (g)', weight: 1 },
  { key: 'p_percentual', label: 'P (%)', weight: 1.3 },
  { key: 'ca_p_percentual', label: 'Ca/P', weight: 1.3 },
]

const linhas = ref([])

const linhasComIndice = computed(() =>
  linhas.value.map((item, index) => ({
    ...item,
    indice: index + 1,
  }))
)

const carregarExigencias = async () => {
  try {
    let pagina = 1
    const registros = []

    while (true) {
      const response = await exigenciasAPI.listar({
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
    console.error('Erro ao carregar exigências:', error)
    linhas.value = []
    totalPaginas.value = 1
  }
}

onMounted(carregarExigencias)
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