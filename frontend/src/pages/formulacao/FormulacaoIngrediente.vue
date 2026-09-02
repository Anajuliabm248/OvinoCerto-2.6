<template>
  <div class="ingredients-page">
    <Header />

    <main class="content">

      <div class="tabs">
        <button
          :class="['tab', { active: activeTab === 'sistema' }]"
          @click="activeTab = 'sistema'"
        >
          Ingredientes do Sistema
        </button>

        <button
          :class="['tab', { active: activeTab === 'usuario' }]"
          @click="activeTab = 'usuario'"
        >
          Ingredientes do Usuário
        </button>
      </div>

      <div class="ingredients-card">

        <div class="top-bar">
          <div>
            <h3>Geração de Formulações</h3>

            <p class="subtitle">
              1. Escolha Ingredientes para sua formulação
            </p>
          </div>

          <button class="btn-action">
            Ingredientes Selecionados
            <span
              v-if="selectedIngredients.length"
              class="selected-count"
            >
              {{ selectedIngredients.length }}
            </span>
          </button>
        </div>

        <div class="table-controls">
          <div class="rows-selector">
            Exibir

            <select>
              <option>10</option>
              <option>25</option>
              <option>50</option>
            </select>

            Linhas
          </div>

          <input
            type="text"
            placeholder="Pesquisar"
            class="search-input"
          />
        </div>

        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Seleção</th>
                <th>Classificação</th>
                <th>Tipo</th>
                <th>Ingrediente</th>
                <th>MS(%)</th>
                <th>PB(%)</th>
                <th>NDT(%)</th>
                <th>FDN(%)</th>
                <th>EE(%)</th>
                <th>C(%)</th>
                <th>P(%)</th>
                <th>R$ (kg/MN)</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="i in 10"
                :key="i"
              >
                <td>
                  <button
                    type="button"
                    :class="['select-dot', { active: isSelected(i) }]"
                    @click="toggleSelection(i)"
                  />
                </td>
                <td>Volumoso</td>
                <td>Forragens Secas</td>
                <td>Alfafa Feno</td>
                <td>89.30</td>
                <td>18.49</td>
                <td>58.51</td>
                <td>46.78</td>
                <td>2.52</td>
                <td>1.32</td>
                <td>1.23</td>
                <td>R$ 5,00</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="bottom-bar">

          <button class="btn-save">
            <RouterLink
              to="/formulacoes/exigencias"
              class="nav-item"
            >
              Próxima etapa
            </RouterLink>
          </button>

          <div class="pagination">
            <button class="page active">1</button>
            <button class="page">2</button>
            <button class="page">3</button>

            <span>...</span>

            <button class="page">99</button>
          </div>

        </div>

      </div>

    </main>
  </div>
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

const selectedIngredients = ref([])
const paginaAtual = ref(1)
const totalPaginas = ref(1)

// Definição das colunas exibidas nesta tabela.
// "weight" define a largura relativa de cada coluna (padrão: 1 se omitido).
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

// Dados exibidos na tabela — em produção virão paginados do banco.
// A própria <Tabela> já cuida da busca (prop "searchable", ligada por
// padrão) e da paginação de 10 em 10, então não precisamos duplicar
// esses controles aqui fora.
const linhas = ref(
  Array.from({ length: 13 }, (_, index) => ({
    id: index + 1,
    classificacao: 'Volumoso',
    tipo: 'Forragens Secas',
    ingrediente: 'Alfafa Feno',
    ms: 89.30,
    pb: 18.49,
    ndt: 58.51,
    fdn: 46.78,
    ee: 2.52,
    ca: 1.32,
    p: 1.23,
    custo: 'R$ 5,00',
  }))
)
</script>

<style scoped>
.btn-selected {
  display: flex;
  align-items: center;
  gap: 8px;

  border: none;

  background: var(--primary-dark);

  color: var(--white);

  padding: 10px 20px;

  border-radius: 999px;

  cursor: pointer;

  font-size: 13px;
}

.selected-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;

  min-width: 20px;
  height: 20px;

  padding: 0 6px;

  border-radius: 999px;

  background: var(--white);

  color: var(--primary-dark);

  font-size: 12px;
  font-weight: 600;
}

@media (max-width: 768px) {
  .btn-selected {
    width: 100%;
    justify-content: center;
  }
}
</style>
