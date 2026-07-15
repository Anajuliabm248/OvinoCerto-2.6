<template>
  <div class="add-ingredient-page">
    <Header />

    <main class="content">
      <div class="add-ingredient-card">
        <div class="top-bar">
          <h3>Cadastro de Ingrediente</h3>
        </div>

        <form class="ingredient-form" @submit.prevent="handleSubmit">
          <div class="form-row">
            <select v-model="form.classificacao" class="form-input">
              <option value="" disabled selected>Classificação</option>
              <option value="volumoso">Volumoso</option>
              <option value="concentrado">Concentrado</option>
              <option value="suplemento">Suplemento</option>
            </select>

            <input
              v-model="form.tipo"
              type="text"
              placeholder="Tipo"
              class="form-input"
            />

            <input
              v-model="form.nome"
              type="text"
              placeholder="Nome de ingrediente"
              class="form-input"
            />
          </div>

          <div class="form-row second-row">
            <input
              v-model="form.ms"
              type="text"
              placeholder="MS (%)"
              class="form-input"
            />
            <input
              v-model="form.pb"
              type="text"
              placeholder="PB (%)"
              class="form-input"
            />
            <input
              v-model="form.ndt"
              type="text"
              placeholder="NDT (%)"
              class="form-input"
            />
            <input
              v-model="form.fdn"
              type="text"
              placeholder="FDN (%)"
              class="form-input"
            />
            <input
              v-model="form.ee"
              type="text"
              placeholder="EE (%)"
              class="form-input"
            />
            <input
              v-model="form.ca"
              type="text"
              placeholder="CA (%)"
              class="form-input"
            />
            <input
              v-model="form.p"
              type="text"
              placeholder="P (%)"
              class="form-input"
            />
            <input
              v-model="form.custo"
              type="text"
              placeholder="Custo (R$)"
              class="form-input"
            />
          </div>

          <div class="preview-box">
            <p class="preview-label">Resumo do ingrediente</p>
            <div class="preview-row">
              <span>{{ form.classificacao || 'Classificação' }}</span>
              <span>{{ form.tipo || 'Tipo' }}</span>
              <span>{{ form.nome || 'Nome de ingrediente' }}</span>
              <span>{{ form.ms || 'MS (%)' }}</span>
              <span>{{ form.pb || 'PB (%)' }}</span>
              <span>{{ form.ndt || 'NDT (%)' }}</span>
              <span>{{ form.fdn || 'FDN (%)' }}</span>
              <span>{{ form.ee || 'EE (%)' }}</span>
              <span>{{ form.ca || 'CA (%)' }}</span>
              <span>{{ form.p || 'P (%)' }}</span>
              <span>{{ form.custo || 'Custo (R$)' }}</span>
            </div>
          </div>

          <div class="form-actions">
            <button type="submit" class="btn-action">
              Cadastrar
            </button>
          </div>
        </form>
      </div>
    </main>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import Header from '@/components/Header.vue'

const form = reactive({
  classificacao: '',
  tipo: '',
  nome: '',
  ms: '',
  pb: '',
  ndt: '',
  fdn: '',
  ee: '',
  ca: '',
  p: '',
  custo: '',
})

function handleSubmit() {
  console.log('Cadastrar ingrediente:', { ...form })
}
</script>

<style scoped>
.add-ingredient-page {
  min-height: 100vh;
  background: var(--background);
}

.content {
  display: flex;
  justify-content: center;
  padding: var(--space-xl) var(--space-lg);
}

.add-ingredient-card {
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

.ingredient-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-sm);
}

.second-row {
  grid-template-columns: repeat(8, minmax(0, 1fr));
}

.form-input {
  width: 100%;
  background: var(--white);
  border: none;
  border-radius: 999px;
  padding: 10px 16px;
  color: var(--text);
  font-size: 14px;
  box-sizing: border-box;
}

select.form-input {
  appearance: none;
  cursor: pointer;
}

.preview-box {
  margin-top: var(--space-sm);
}

.preview-label {
  margin: 0 0 8px;
  color: var(--white);
  font-size: 13px;
}

.preview-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  background: var(--white);
  border-radius: 999px;
  padding: 12px 20px;
  color: #666;
  font-size: 14px;
  flex-wrap: wrap;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-md);
}

.btn-action {
  border: none;
  background: var(--primary-dark);
  color: var(--white);
  padding: 10px 28px;
  border-radius: 999px;
  cursor: pointer;
  transition: .2s ease;
}

.btn-action:hover {
  filter: brightness(1.1);
}

@media (max-width: 1024px) {
  .form-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .second-row {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .preview-row {
    border-radius: var(--radius-lg);
  }
}

@media (max-width: 768px) {
  .content {
    padding: var(--space-md);
  }

  .add-ingredient-card {
    padding: var(--space-md);
  }

  .form-row,
  .second-row {
    grid-template-columns: 1fr;
  }

  .form-actions {
    justify-content: stretch;
  }

  .btn-action {
    width: 100%;
  }
}
</style>
