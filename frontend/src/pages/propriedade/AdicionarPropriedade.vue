<template>
  <PageCard title="Cadastro de Propriedade" size="form">
    <template #top-bar-extra>
      <Botao label="Voltar" to="/propriedades" variant="ghost" />
    </template>

    <form class="property-form" @submit.prevent="handleSubmit">
      <div class="form-row">
        <CampoTexto v-model="form.identificacao" placeholder="Identificação" />
        <CampoTexto v-model="form.cnpj" placeholder="CNPJ" />
        <CampoTexto v-model="form.proprietario" placeholder="Proprietário" />
      </div>

      <div class="form-row second-row">
        <CampoTexto v-model="form.telefone" placeholder="Telefone" />
        <select v-model="form.estado" class="form-input">
          <option value="" disabled>Estado</option>
          <option v-for="uf in estados" :key="uf.sigla" :value="uf.sigla">
            {{ uf.sigla }} - {{ uf.nome }}
          </option>
        </select>
        <CampoTexto v-model="form.cidade" placeholder="Cidade" />
        <CampoTexto v-model="form.localidade" placeholder="Localidade" />
      </div>

      <p class="preview-label">Exemplo de visualização na relação de propriedades:</p>

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
        <Botao label="Cadastrar" type="submit" />
      </div>
    </form>
  </PageCard>
</template>

<script setup>
import { reactive } from 'vue'
import PageCard from '@/components/ui/PageCard.vue'
import CampoTexto from '@/components/ui/CampoTexto.vue'
import Botao from '@/components/ui/Botao.vue'

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
.property-form {
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  gap: var(--space-sm);
  min-height: 0;
  height: 100%;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-sm);
}

.second-row {
  grid-template-columns: repeat(4, minmax(0, 1fr));
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
  flex-wrap: wrap;
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

@media (max-width: 1024px) {
  .form-row,
  .second-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .preview-row {
    border-radius: var(--radius-lg);
  }
}

@media (max-width: 768px) {
  .form-row,
  .second-row {
    grid-template-columns: 1fr;
  }

  .form-actions {
    justify-content: stretch;
  }

  .form-actions .botao {
    width: 100%;
  }
}
</style>