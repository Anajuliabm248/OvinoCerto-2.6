<template>
  <div class="ovinos-page">
    <Header />

    <main class="content">
      <div class="ovinos-card">

        <div class="top-bar">
          <h3>Relação de Ovinos/lotes</h3>

          <div class="actions">
            <button class="btn-action">
              Editar Ovinos/lotes
            </button>
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
                <th>Nome lote</th>
                <th>Raça</th>
                <th>Sistema</th>
                <th>categoria</th>
                <th>fase</th>
                <th>PV</th>
                <th>GMD esperado</th>
                <th>Quantidade</th>
                <th>idade</th>
                <th>Tipo de Parto</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="i in 10"
                :key="i"
              >
                <td>LOTE TESTE 01</td>
                <td>Santa Inês</td>
                <td>Semi-Confinado</td>
                <td>Cordeiros</td>
                <td>Crescimento</td>
                <td>28 kg</td>
                <td>0,250 kg/dia</td>
                <td>35</td>
                <td>90 dias</td>
                <td>Parto Simples</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination">
          <button class="page active">1</button>
          <button class="page">2</button>
          <button class="page">3</button>

          <span>...</span>

          <button class="page">99</button>
        </div>

      </div>
    </main>
  </div>
</template>

<script setup>
import Header from '@/components/Header.vue'
</script>

<style scoped>
.ovinos-page {
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

.ovinos-card {
  width: 100%;
  max-width: 1400px;

  background: var(--card-bg);

  border-radius: 24px;

  padding: var(--space-lg);

  box-shadow: var(--shadow-md);
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;

  margin-bottom: var(--space-md);
}

.top-bar h3 {
  margin: 0;
  color: var(--white);
  font-weight: 500;
}

.actions {
  display: flex;
  gap: var(--space-sm);
}

.btn-action {
  border: none;

  background: var(--primary-dark);

  color: var(--white);

  padding: 10px 20px;

  border-radius: 999px;

  cursor: pointer;

  transition: .2s ease;
}

.btn-action:hover {
  filter: brightness(1.1);
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

  min-width: 900px;
}

thead {
  background: #e6e2d3;
}

th {
  text-align: left;

  padding: 12px 12px;
  line-height: 20px;

  font-size: 14px;

  color: var(--text);
}

td {
  padding: 8px 12px;

  border-top: 1px solid #d8d3c4;
  line-height: 20px;

  color: #666;
}

tbody tr:nth-child(even) {
  background: #f2efe2;
}

tbody tr:hover {
  background: #f8f7f2;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  align-items: center;

  gap: 6px;

  margin-top: var(--space-md);
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

@media (max-width: 1024px) {
  .top-bar {
    flex-direction: column;
    align-items: flex-start;

    gap: var(--space-sm);
  }

  .table-controls {
    flex-direction: column;
    align-items: flex-start;

    gap: var(--space-sm);
  }

  .search-input {
    width: 100%;
  }

  .actions {
    width: 100%;
    flex-wrap: wrap;
  }
}

@media (max-width: 768px) {
  .content {
    padding: var(--space-md);
  }

  .ovinos-card {
    padding: var(--space-md);
  }

  .actions {
    flex-direction: column;
  }

  .btn-action {
    width: 100%;
  }
}
</style>