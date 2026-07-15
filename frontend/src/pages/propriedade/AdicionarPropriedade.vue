<template>
  <div class="add-property-page">
    <Header />

    <main class="content">
      <div class="add-property-card">

        <div class="top-bar">
          <h3>Cadastro de Propriedade</h3>
        </div>

        <form class="property-form" @submit.prevent="handleSubmit">
          <div class="form-row">
            <input
              v-model="form.identificacao"
              type="text"
              placeholder="Identificação"
              class="form-input"
            />
            <input
              v-model="form.cnpj"
              type="text"
              placeholder="CNPJ"
              class="form-input"
            />
            <input
              v-model="form.proprietario"
              type="text"
              placeholder="Proprietário"
              class="form-input"
            />
          </div>

          <div class="form-row">
            <input
              v-model="form.telefone"
              type="text"
              placeholder="Telefone"
              class="form-input"
            />
            <select
              v-model="form.estado"
              class="form-input"
            >
              <option value="" disabled selected>Estado</option>
              <option
                v-for="uf in estados"
                :key="uf.sigla"
                :value="uf.sigla"
              >
                {{ uf.sigla }} - {{ uf.nome }}
              </option>
            </select>
            <input
              v-model="form.cidade"
              type="text"
              placeholder="Cidade"
              class="form-input"
            />
            <input
              v-model="form.localidade"
              type="text"
              placeholder="Localidade"
              class="form-input"
            />
          </div>

          <p class="preview-label">
            Exemplo de visualização na relação de propriedades:
          </p>

          <div class="preview-row">
            <span>{{ form.identificacao || 'TESTE' }}</span>
            <span>{{ form.cnpj || '00.000.000/000-00' }}</span>
            <span>{{ form.proprietario || 'TESTE' }}</span>
            <span>{{ form.telefone || '(12) 34567-8909' }}</span>
            <span>{{ form.estado || 'AC - Acre' }}</span>
            <span>{{ form.cidade || 'Acrelândia' }}</span>
            <span>{{ form.localidade || 'D' }}</span>
            <span class="preview-options">X E</span>
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

const estados = [
  { sigla: 'AC', nome: 'Acre' },
  { sigla: 'AL', nome: 'Alagoas' },
  { sigla: 'AP', nome: 'Amapá' },
  { sigla: 'AM', nome: 'Amazonas' },
  { sigla: 'BA', nome: 'Bahia' },
  { sigla: 'CE', nome: 'Ceará' },
  { sigla: 'DF', nome: 'Distrito Federal' },
  { sigla: 'ES', nome: 'Espírito Santo' },
  { sigla: 'GO', nome: 'Goiás' },
  { sigla: 'MA', nome: 'Maranhão' },
  { sigla: 'MT', nome: 'Mato Grosso' },
  { sigla: 'MS', nome: 'Mato Grosso do Sul' },
  { sigla: 'MG', nome: 'Minas Gerais' },
  { sigla: 'PA', nome: 'Pará' },
  { sigla: 'PB', nome: 'Paraíba' },
  { sigla: 'PR', nome: 'Paraná' },
  { sigla: 'PE', nome: 'Pernambuco' },
  { sigla: 'PI', nome: 'Piauí' },
  { sigla: 'RJ', nome: 'Rio de Janeiro' },
  { sigla: 'RN', nome: 'Rio Grande do Norte' },
  { sigla: 'RS', nome: 'Rio Grande do Sul' },
  { sigla: 'RO', nome: 'Rondônia' },
  { sigla: 'RR', nome: 'Roraima' },
  { sigla: 'SC', nome: 'Santa Catarina' },
  { sigla: 'SP', nome: 'São Paulo' },
  { sigla: 'SE', nome: 'Sergipe' },
  { sigla: 'TO', nome: 'Tocantins' },
]

const form = reactive({
  identificacao: '',
  cnpj: '',
  proprietario: '',
  telefone: '',
  estado: '',
  cidade: '',
  localidade: '',
})

function handleSubmit() {
  // TODO: integrar com a API de cadastro de propriedades
  console.log('Cadastrar propriedade:', { ...form })
}
</script>

<style scoped>
.add-property-page {
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

.add-property-card {
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

.property-form {
  display: flex;
  flex-direction: column;

  gap: var(--space-sm);
}

.form-row {
  display: flex;

  gap: var(--space-sm);
}

.form-input {
  flex: 1;

  background: var(--white);

  border: none;
  border-radius: 999px;

  padding: 10px 20px;

  color: var(--text);

  font-size: 14px;
}

select.form-input {
  appearance: none;
  cursor: pointer;
}

.preview-label {
  margin: var(--space-md) 0 0;

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

  padding: 12px 24px;

  color: #666;
  font-size: 14px;
}

.preview-options {
  font-weight: 600;
  color: var(--text);
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
    flex-wrap: wrap;
  }

  .form-input {
    flex: 1 1 45%;
  }

  .preview-row {
    flex-wrap: wrap;
    border-radius: var(--radius-lg);
  }
}

@media (max-width: 768px) {
  .content {
    padding: var(--space-md);
  }

  .add-property-card {
    padding: var(--space-md);
  }

  .form-row {
    flex-direction: column;
  }

  .form-input {
    flex: 1 1 100%;
  }

  .form-actions {
    justify-content: stretch;
  }

  .btn-action {
    width: 100%;
  }
}
</style>