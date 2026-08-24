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
              1. Escolha Ingredientes para sua formulação, sempre adicionar os volumosos e de maior quantidade primeiro
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
import Header from '@/components/Header.vue'

const activeTab = ref('sistema')

const selectedIngredients = ref([])

function isSelected(id) {
  return selectedIngredients.value.includes(id)
}

function toggleSelection(id) {
  if (isSelected(id)) {
    selectedIngredients.value = selectedIngredients.value.filter(
      (item) => item !== id
    )
  } else {
    selectedIngredients.value.push(id)
  }
}
</script>

<style scoped>
.ingredients-page {
  min-height: 100vh;
  background: var(--background);
}

.content {
  display: flex;
  flex-direction: column;
  align-items: center;

  padding: 24px;
}

.tabs {
  width: 100%;
  max-width: 1500px;

  display: flex;
  gap: 2px;

  margin-bottom: -1px;

  padding-left: 32px;
}

.tab {
  border: none;

  padding: 10px 16px;

  border-radius: 18px 18px 0 0;

  cursor: pointer;

  background: var(--primary-dark);

  color: var(--white);

  font-size: 16px;
}

.tab.active {
  background: var(--card-bg);
  opacity: 1;
}

.ingredients-card {
  width: 100%;
  max-width: 1500px;

  background: var(--card-bg);

  border-radius: 24px;

  padding: var(--space-lg);

  box-shadow: var(--shadow-md);
}

.tabs {
  width: 100%;
  max-width: 1500px;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;

  margin-bottom: var(--space-md);
}

.top-bar h3 {
  margin: 0;

  color: var(--white);

  font-weight: 500;
}

.subtitle {
  margin: 0;

  color: rgba(255,255,255,.75);

  font-size: 14px;

  margin-bottom: -16px;
  margin-top: -4px;
}

.btn-action {
  display: flex;
  align-items: center;
  gap: 8px;

  border: none;

  background: var(--primary-dark);

  color: var(--white);

  padding: 10px 20px;

  border-radius: 999px;

  cursor: pointer;
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

.table-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;

  margin-bottom: var(--space-sm);
}

.rows-selector {
  display: flex;
  align-items: center;
  gap: 8px;

  color: var(--white);
}

.rows-selector select {
  width: auto;

  border-radius: 999px;

  padding: 4px 10px;
}

.search-input {
  width: 220px;

  background: var(--white);

  border-radius: 999px;

  padding: 4px 16px;
}

.table-wrapper {
  overflow-x: auto;

  border-radius: var(--radius-lg);

  background: var(--white);

  display: flex;

  justify-content: center;
}

table {
  width: 100%;

  border-collapse: collapse;

  table-layout: auto;
}

thead {
  background: #e6e2d3;
}

th {
  padding: 12px 10px;
  padding-left: 32px;

  text-align: left;
  line-height: 20px;

  font-size: 13px;

  color: var(--text);
}

td {
  padding: 8px 12px;
  padding-left: 32px;

  border-top: 1px solid #d8d3c4;
  line-height: 20px;

  color: #666;
}

tbody tr:hover {
  background: #f8f7f2;
}

.select-dot {
  width: 20px;
  height: 20px;

  border-radius: 50%;

  border: 2px solid #bbb;

  background: var(--white);

  cursor: pointer;

  padding: 0;

  transition: .15s ease;
}

.select-dot.active {
  background: var(--primary-dark);
  border-color: var(--primary-dark);
}

.bottom-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;

  margin-top: var(--space-md);
}

.btn-save {
  border: none;

  background: var(--primary-dark);

  color: var(--white);

  padding: 12px 24px;

  border-radius: 999px;

  cursor: pointer;
}

.pagination {
  display: flex;
  align-items: center;

  gap: 6px;
}

.page {
  width: 30px;
  height: 30px;

  border: none;

  border-radius: 50%;

  cursor: pointer;

  background: rgba(255,255,255,.15);

  color: var(--white);
}

.page.active {
  background: var(--white);

  color: var(--primary-dark);
}

.pagination span {
  color: var(--white);
}

@media (max-width: 768px) {
  .top-bar,
  .bottom-bar,
  .table-controls {
    flex-direction: column;
    align-items: flex-start;

    gap: var(--space-sm);
  }

  .search-input {
    width: 100%;
  }

  .btn-action,
  .btn-save {
    width: 100%;
  }
}
</style>