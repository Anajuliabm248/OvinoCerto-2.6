<template>
  <PageCard title="Cadastro de Ingrediente" size="form">
    <template #top-bar-extra>
      <Botao label="Voltar" to="/ingredientes" variant="ghost" />
    </template>

    <form class="ingredient-form" @submit.prevent="handleSubmit">

      <div class="form-row">
        <Seletor v-model="form.classificacao" placeholder="Classificação" :options="opcoesClassificacao" />
        <Seletor v-model="form.tipo" placeholder="Tipo" :options="opcoesTipo" />
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

      <div v-if="mensagem" class="status success">{{ mensagem }}</div>
      <div v-if="erro" class="status error">{{ erro }}</div>

      <div class="form-actions">
        <Botao label="Cadastrar" type="submit" />
      </div>

    </form>
  </PageCard>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageCard from '@/components/ui/PageCard.vue'
import CampoTexto from '@/components/ui/CampoTexto.vue'
import Seletor from '@/components/ui/Seletor.vue'
import Botao from '@/components/ui/Botao.vue'
import { ingredientesAPI } from '@/services/api'

const router = useRouter()
const mensagem = ref('')
const erro = ref('')

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
]

const opcoesTipo = computed(() => {
  if (form.classificacao === 'volumoso') {
    return [
      { value: 'forragens_secas', label: 'Forragens Secas' },
      { value: 'forragens_verdes', label: 'Forragens Verdes' },
      { value: 'silagens', label: 'Silagens' },
    ]
  }

  if (form.classificacao === 'concentrado') {
    return [
      { value: 'energetico', label: 'Energético' },
      { value: 'proteico', label: 'Proteico' },
      { value: 'mineral', label: 'Mineral' },
      { value: 'aditivos', label: 'Aditivos' },
    ]
  }

  return []
})

function parseDecimal(value) {
  if (value === '' || value === null || value === undefined) return NaN

  const texto = String(value).trim()

  if (texto.includes(',') && texto.includes('.')) {
    const normalizado = texto.replace(/\./g, '').replace(',', '.')
    const numero = Number(normalizado)
    return Number.isFinite(numero) ? numero : NaN
  }

  if (texto.includes(',')) {
    const normalizado = texto.replace(',', '.')
    const numero = Number(normalizado)
    return Number.isFinite(numero) ? numero : NaN
  }

  const numero = Number(texto)
  return Number.isFinite(numero) ? numero : NaN
}

async function handleSubmit() {
  erro.value = ''
  mensagem.value = ''

  const camposNumericos = {
    ms: 'MS',
    pb: 'PB',
    ndt: 'NDT',
    fdn: 'FDN',
    ee: 'EE',
    ca: 'Ca',
    p: 'P',
    custo: 'Custo',
  }

  for (const [campo, label] of Object.entries(camposNumericos)) {
    const valor = parseDecimal(form[campo])
    if (Number.isNaN(valor)) {
      erro.value = `Campo ${label} inválido. Use números como 25,80 ou 25.80.`
      return
    }
    form[campo] = String(valor)
  }

  try {
    const payload = {
      classificacao: form.classificacao,
      tipo: form.tipo,
      nome: form.nome.trim(),
      ms: parseDecimal(form.ms),
      pb: parseDecimal(form.pb),
      ndt: parseDecimal(form.ndt),
      fdn: parseDecimal(form.fdn),
      ee: parseDecimal(form.ee),
      ca: parseDecimal(form.ca),
      p: parseDecimal(form.p),
      custo_kg: parseDecimal(form.custo),
    }

    await ingredientesAPI.criar(payload)
    mensagem.value = 'Ingrediente salvo com sucesso na aba de usuário.'

    setTimeout(() => {
      router.push('/ingredientes')
    }, 500)
  } catch (error) {
    const detail = error.response?.data
    const message =
      detail?.non_field_errors?.[0] ||
      detail?.detail ||
      Object.entries(detail || {}).flatMap(([campo, erros]) => Array.isArray(erros) ? erros : [erros]).join(' ') ||
      'Não foi possível salvar o ingrediente.'
    erro.value = message
    console.error('Erro ao criar ingrediente:', error)
  }
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

.status {
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 500;
}

.status.success {
  background: rgba(95, 115, 23, 0.12);
  color: #2f3d00;
}

.status.error {
  background: rgb(255, 0, 0);
  color: #000000;
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
