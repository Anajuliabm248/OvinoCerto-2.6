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
        @update:currentPage="paginaAtual = $event"
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

const paginaAtual = ref(1)
const totalPaginas = ref(1)

const colunas = [
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
</script>

<style scoped>
.ovinos-actions {
  display: flex;
  gap: var(--space-sm);
  flex-wrap: wrap;
}
</style>