<template>
  <div class="requirements-page">
    <Header />

    <main class="content">

      <div class="requirements-card">

        <div class="top-bar">
          <div>
            <h3>Geração de Formulações</h3>

            <p class="subtitle">
              2. Escolha as exigências nutricionais
            </p>
          </div>
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
                <th>ID</th>
                <th>Categoria</th>
                <th>Fase</th>
                <th>PV(kg)</th>
                <th>Tipo Parto</th>
                <th>PV Nascença (kg)</th>
                <th>Prod. Leite (kg/dia)</th>
                <th>GMD(kg)</th>
                <th>PV(%)</th>
                <th>CMS(kg)</th>
                <th>PB(g)</th>
                <th>PB</th>
                <th>NDT(kg)</th>
                <th>NDT(%)</th>
                <th>FDN(kg)</th>
                <th>³FDN(%)</th>
                <th>EE(kg)</th>
                <th>⁴EE(%)</th>
                <th>Ca(g)</th>
                <th>Ca(%)</th>
                <th>P(g)</th>
                <th>P(%)</th>
                <th>Ca/P</th>
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
                <td>1</td>
                <td>Cordeiro(a)<br>(4 meses)</td>
                <td>Crescimento</td>
                <td>20</td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
                <td>0.1000</td>
                <td>2.8600</td>
                <td>0.5720</td>
                <td>73.0000</td>
                <td>12.7622</td>
                <td>0.3000</td>
                <td>52.4476</td>
                <td>0.1716</td>
                <td>30.0000</td>
                <td>0.0400</td>
                <td>7.0000</td>
                <td>2.3000</td>
                <td>0.4021</td>
                <td>1.5000</td>
                <td>0.2622</td>
                <td>1.5333</td>
              </tr>

            </tbody>

          </table>

        </div>

        <div class="bottom-bar">

          <button class="btn-save">
            <RouterLink
              to="/formulacoes/dashboard"
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

const selectedRequirements = ref([])

function isSelected(id) {
  return selectedRequirements.value.includes(id)
}

function toggleSelection(id) {
  if (isSelected(id)) {
    selectedRequirements.value = selectedRequirements.value.filter(
      (item) => item !== id
    )
  } else {
    selectedRequirements.value.push(id)
  }
}
</script>

<style scoped>
.requirements-page {
  min-height: 100vh;

  background: var(--background);
}

.content {
  display: flex;
  justify-content: center;

  padding:
    var(--space-xl)
    var(--space-lg);
}

.requirements-card {
  width: 100%;
  max-width: 1800px;

  background: var(--card-bg);

  border-radius: 24px;

  padding: var(--space-lg);

  box-shadow: var(--shadow-md);
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

  margin-top: -4px;
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
}

table {
  width: 100%;

  border-collapse: collapse;

  white-space: nowrap;
}

thead {
  background: #e6e2d3;
}

th {
  padding: 12px 10px;

  text-align: center;
  line-height: 20px;

  font-size: 13px;

  font-weight: 500;

  color: var(--text);
}

td {
  padding: 2px 10px;

  text-align: center;

  font-size: 14px;
  letter-spacing: -0.7px;
  line-height: 20px;

  border-top: 1px solid #d8d3c4;

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

@media (max-width: 1200px) {
  .table-wrapper {
    overflow-x: auto;
  }
}

@media (max-width: 768px) {
  .table-controls,
  .bottom-bar {
    flex-direction: column;
    align-items: flex-start;

    gap: var(--space-sm);
  }

  .search-input {
    width: 100%;
  }

  .content {
    padding: var(--space-md);
  }

  .requirements-card {
    padding: var(--space-md);
  }

  .btn-save {
    width: 100%;
  }
}
</style>