<template>
  <PageCard title="Cadastro de Ingrediente" size="form">
    <template #top-bar-extra>
      <Botao label="Voltar" to="/ingredientes" variant="ghost" />
    </template>

    <form class="ingredient-form" @submit.prevent="handleSubmit">

      <div class="form-row">
        <Seletor v-model="form.classificacao" placeholder="Classificação" :options="opcoesClassificacao" />
        <CampoTexto v-model="form.tipo" placeholder="Tipo" />
        <CampoTexto v-model="form.nome" placeholder="Nome de ingrediente" />
      </div>

      <div class="form-row second-row">
        <CampoTexto v-model="form.ms" placeholder="MS (%)" />
        <CampoTexto v-model="form.pb" placeholder="PB (%)" />
        <CampoTexto v-model="form.ndt" placeholder="NDT (%)" />
        <CampoTexto v-model="form.fdn" placeholder="FDN (%)" />
        <CampoTexto v-model="form.ee" placeholder="EE (%)" />
        <CampoTexto v-model="form.ca" placeholder="CA (%)" />
        <CampoTexto v-model="form.p" placeholder="P (%)" />
        <CampoTexto v-model="form.custo" placeholder="Custo (R$)" />
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
        <Botao label="Cadastrar" type="submit" />
      </div>

    </form>
  </PageCard>
</template>

<script setup>
import { reactive } from 'vue'
import PageCard from '@/components/ui/PageCard.vue'
import CampoTexto from '@/components/ui/CampoTexto.vue'
import Seletor from '@/components/ui/Seletor.vue'
import Botao from '@/components/ui/Botao.vue'

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

const opcoesClassificacao = [
  { value: 'volumoso', label: 'Volumoso' },
  { value: 'concentrado', label: 'Concentrado' },
  { value: 'suplemento', label: 'Suplemento' },
]

function handleSubmit() {
  console.log('Cadastrar ingrediente:', { ...form })
}
</script>

<style scoped>
.ingredient-form {
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  gap: var(--space-sm);
  min-height: 0;
  height: 100%;
}

/* Layout de grade específico desta página (nº de colunas por linha) */
.form-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-sm);
}

.second-row {
  grid-template-columns: repeat(8, minmax(0, 1fr));
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
