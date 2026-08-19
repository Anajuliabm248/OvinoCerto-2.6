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
  { key: 'nome', label: 'Nome', weight: 2 },
  { key: 'cnpj', label: 'CNPJ', weight: 1.5 },
  { key: 'proprietario', label: 'Proprietário', weight: 1.8 },
  { key: 'telefone', label: 'Telefone', weight: 1.2 },
  { key: 'estado', label: 'Estado', weight: 1 },
  { key: 'cidade', label: 'Cidade', weight: 1 },
  { key: 'localidade', label: 'Localidade', weight: 1 },
  { key: 'opcoes', label: 'Opções', weight: 0.8 },
]

const linhas = ref(
  Array.from({ length: 10 }, (_, index) => ({
    id: index + 1,
    nome: 'Fazenda Exemplo',
    cnpj: '00.000.000/0001-00',
    proprietario: 'João da Silva',
    telefone: '(12) 34567-8909',
    estado: 'AC',
    cidade: 'Acrelândia',
    localidade: 'Sede',
    opcoes: 'X  E',
  }))
)
</script>

<style scoped>
.properties-actions {
  display: flex;
  gap: var(--space-sm);
  flex-wrap: wrap;
}
</style>