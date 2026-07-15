<template>
  <div class="add-lot-page">
    <Header />

    <main class="content">
      <div class="add-lot-card">
        <div class="top-bar">
          <h3>Cadastro de Ovinos/Lote</h3>
        </div>

        <form class="lot-form" @submit.prevent="handleSubmit">
          <div class="form-row">
            <input
              v-model="form.nomeLote"
              type="text"
              placeholder="Nome do lote"
              class="form-input"
            />
            <input
              v-model="form.raca"
              type="text"
              placeholder="Raça"
              class="form-input"
            />
            <select v-model="form.sistema" class="form-input">
              <option value="" disabled selected>Sistema</option>
              <option value="pastagem">Pastagem</option>
              <option value="confinamento">Confinamento</option>
              <option value="semi-confinamento">Semi-confinamento</option>
            </select>
            <select v-model="form.fase" class="form-input">
              <option value="" disabled selected>Fase</option>
              <option value="crescimento">Crescimento</option>
              <option value="terminacao">Terminação</option>
              <option value="reproducao">Reprodução</option>
            </select>
          </div>

          <div class="form-row second-row">
            <input
              v-model="form.pv"
              type="text"
              placeholder="PV"
              class="form-input"
            />
            <input
              v-model="form.gmdEsperado"
              type="text"
              placeholder="GMD esperado"
              class="form-input"
            />
            <input
              v-model="form.unidades"
              type="number"
              min="1"
              placeholder="Unidades"
              class="form-input"
            />
            <input
              v-model="form.idade"
              type="number"
              min="0"
              placeholder="Idade"
              class="form-input"
            />
            <select v-model="form.tipoParto" class="form-input">
              <option value="" disabled selected>Tipo de parto</option>
              <option value="simples">Simples</option>
              <option value="duplo">Duplo</option>
              <option value="triplo">Triplo</option>
            </select>
          </div>

          <div class="preview-box">
            <p class="preview-label">Resumo do lote</p>
            <div class="preview-row">
              <span>{{ form.nomeLote || 'Nome do lote' }}</span>
              <span>{{ form.raca || 'Raça' }}</span>
              <span>{{ form.sistema || 'Sistema' }}</span>
              <span>{{ form.fase || 'Fase' }}</span>
              <span>{{ form.pv || 'PV' }}</span>
              <span>{{ form.gmdEsperado || 'GMD esperado' }}</span>
              <span>{{ form.unidades || 'Unidades' }}</span>
              <span>{{ form.idade || 'Idade' }}</span>
              <span>{{ form.tipoParto || 'Tipo de parto' }}</span>
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
  nomeLote: '',
  raca: '',
  sistema: '',
  fase: '',
  pv: '',
  gmdEsperado: '',
  unidades: '',
  idade: '',
  tipoParto: '',
})

function handleSubmit() {
  console.log('Cadastrar lote:', { ...form })
}
</script>

<style scoped>
.add-lot-page {
  min-height: 100vh;
  background: var(--background);
}

.content {
  display: flex;
  justify-content: center;
  padding: var(--space-xl) var(--space-lg);
}

.add-lot-card {
  width: 100%;
  max-width: 1200px;
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

.lot-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-sm);
}

.second-row {
  grid-template-columns: repeat(5, minmax(0, 1fr));
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
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .preview-row {
    border-radius: var(--radius-lg);
  }
}

@media (max-width: 768px) {
  .content {
    padding: var(--space-md);
  }

  .add-lot-card {
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
