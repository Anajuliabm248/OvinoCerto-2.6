<template>
  <div class="properties-page">
    <Header />

    <main class="content">
      <div class="properties-card">

        <div class="top-bar">
          <h3>Relação de Propriedades</h3>

          <div class="actions">
            <button class="btn-action">
              Ver Ovinos/lotes
            </button>

            <button class="btn-action">
              Adicionar Propriedade
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
                <th>Nome</th>
                <th>CNPJ</th>
                <th>Proprietário</th>
                <th>Telefone</th>
                <th>Estado</th>
                <th>Cidade</th>
                <th>Localidade</th>
                <th>Opções</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="i in 10"
                :key="i"
              >
                <td>TESTE</td>
                <td>00.000.000/000-00</td>
                <td>TESTE</td>
                <td>(12) 34567-8909</td>
                <td>AC - Acre</td>
                <td>Acrelândia</td>
                <td>D</td>
                <td>
                  <button class="option-btn">X</button>
                  <button class="option-btn">E</button>
                </td>
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
.properties-page {
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

.properties-card {
  width: 100%;
  max-width: 1100px;

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

tbody tr:hover {
  background: #f8f7f2;
}

.option-btn {
  border: none;

  background: transparent;

  color: var(--text);

  cursor: pointer;

  font-weight: 600;
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

  .properties-card {
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