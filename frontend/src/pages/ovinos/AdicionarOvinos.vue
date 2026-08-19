<template>
  <PageCard title="Cadastro de Ovinos/Lote" size="form">
    <template #top-bar-extra>
      <Botao
        label="Voltar"
        to="/propriedades/ovinos"
        variant="ghost"
      />
    </template>

    <form class="lote-form" @submit.prevent="handleSubmit">

      <div class="form-row">
        <CampoTexto v-model="form.nomeLote" placeholder="Nome do lote" />
        <CampoTexto v-model="form.raca" placeholder="Raça" />
        <Seletor v-model="form.sistema" placeholder="Sistema" :options="opcoesSistema" />
        <Seletor v-model="form.fase" placeholder="Fase" :options="opcoesFase" />
      </div>

      <div class="form-row second-row">
        <CampoTexto v-model="form.pv" placeholder="PV" />
        <CampoTexto v-model="form.gmdEsperado" placeholder="GMD esperado" />
        <CampoTexto v-model="form.unidades" type="number" min="1" placeholder="Unidades" />
        <CampoTexto v-model="form.idade" type="number" min="0" placeholder="Idade" />
        <Seletor v-model="form.tipoParto" placeholder="Tipo de parto" :options="opcoesTipoParto" />
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

const opcoesSistema = [
  { value: 'pastagem', label: 'Pastagem' },
  { value: 'confinamento', label: 'Confinamento' },
  { value: 'semi-confinamento', label: 'Semi-confinamento' },
]

const opcoesFase = [
  { value: 'crescimento', label: 'Crescimento' },
  { value: 'terminacao', label: 'Terminação' },
  { value: 'reproducao', label: 'Reprodução' },
]

const opcoesTipoParto = [
  { value: 'simples', label: 'Simples' },
  { value: 'duplo', label: 'Duplo' },
  { value: 'triplo', label: 'Triplo' },
]

function handleSubmit() {
  console.log('Cadastrar lote:', { ...form })
}
</script>

<style scoped>
.lote-form {
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  gap: var(--space-sm);
  min-height: 0;
  height: 100%;
}

/* Layout de grade específico desta página (nº de colunas por linha) */
.form-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-sm);
}

.second-row {
  grid-template-columns: repeat(5, minmax(0, 1fr));
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
