<template>
  <PageCard
    title="Geração de Formulações"
    subtitle="2. Escolha as exigências nutricionais"
  >
    <Tabela
      :columns="colunas"
      :rows="linhas"
      v-model:selected="selecionados"
      :current-page="paginaAtual"
      @update:current-page="paginaAtual = $event"
      @update:total-pages="totalPaginas = $event"
    />

    <template #actions>
      <Botao label="Próxima etapa" :to="{ path: '/formulacoes/dashboard' }" />
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
import Tabela from '@/components/ui/Tabela.vue'
import Botao from '@/components/ui/Botao.vue'
import Paginacao from '@/components/ui/Paginacao.vue'

const selecionados = ref([])
const paginaAtual = ref(1)
const totalPaginas = ref(1)

// Definição das colunas exibidas nesta tabela específica.
// "wrap: true" permite quebra de linha (ex.: "Cordeiro(a)\n(4 meses)")
// "weight" define a largura relativa de cada coluna (padrão: 1 se omitido).
// Ex.: categoria e os rótulos mais longos recebem mais espaço lateral;
// colunas curtas como "PB" ou "Ca/P" ficam mais estreitas.
const colunas = [
  { key: 'categoria', label: 'Categoria', wrap: true, weight: 2 },
  { key: 'fase', label: 'Fase', weight: 1.8 },
  { key: 'pv', label: 'PV(kg)', weight: 1 },
  { key: 'tipoParto', label: 'Tipo Parto', weight: 1.2 },
  { key: 'pvNascenca', label: 'PV Nascença (kg)', weight: 1.6 },
  { key: 'prodLeite', label: 'Prod. Leite (kg/dia)', weight: 1.6 },
  { key: 'gmd', label: 'GMD(kg)', weight: 1 },
  { key: 'pvPercent', label: 'PV(%)', weight: 1 },
  { key: 'cms', label: 'CMS(kg)', weight: 1 },
  { key: 'pbG', label: 'PB(g)', weight: 1 },
  { key: 'pb', label: 'PB', weight: 1.3 },
  { key: 'ndtKg', label: 'NDT(kg)', weight: 1 },
  { key: 'ndtPercent', label: 'NDT(%)', weight: 1.3 },
  { key: 'fdnKg', label: 'FDN(kg)', weight: 1.3 },
  { key: 'fdnPercent', label: '³FDN(%)', weight: 1 },
  { key: 'eeKg', label: 'EE(kg)', weight: 1 },
  { key: 'eePercent', label: '⁴EE(%)', weight: 1 },
  { key: 'caG', label: 'Ca(g)', weight: 1 },
  { key: 'caPercent', label: 'Ca(%)', weight: 1.3 },
  { key: 'pG', label: 'P(g)', weight: 1 },
  { key: 'pPercent', label: 'P(%)', weight: 1.3 },
  { key: 'caP', label: 'Ca/P', weight: 1.3 },
]

// Dados exibidos na tabela — em produção virão paginados do banco
// (a própria <Tabela> já fatia automaticamente em dezenas: 1-10, 11-20...)
const linhas = [
  ...Array.from({ length: 21 }, (_, idx) => ({
    id: idx + 1,
    categoria: 'Cordeiro(a)\n(4 meses)',
    fase: 'Crescimento',
    pv: 20,
    tipoParto: '-',
    pvNascenca: '-',
    prodLeite: '-',
    gmd: 0.1,
    pvPercent: 2.86,
    cms: 0.572,
    pbG: 73,
    pb: 12.7622,
    ndtKg: 0.3,
    ndtPercent: 52.4476,
    fdnKg: 0.1716,
    fdnPercent: 30,
    eeKg: 0.04,
    eePercent: 7,
    caG: 2.3,
    caPercent: 0.4021,
    pG: 1.5,
    pPercent: 0.2622,
    caP: 1.5333,
  }))
]
</script>
