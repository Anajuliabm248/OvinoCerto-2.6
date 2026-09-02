<template>
  <PageCard title="Cadastro de Propriedade" size="form">
    <template #top-bar-extra>
      <Botao label="Voltar" to="/propriedades" variant="ghost" />
    </template>

    <form class="property-form" @submit.prevent="handleSubmit">
      <div class="form-row">
        <CampoTexto v-model="form.nome" placeholder="Nome da propriedade" />
        <CampoTexto v-model="form.proprietario" placeholder="Proprietário" />
        <CampoTexto v-model="form.telefone" placeholder="Telefone" />
      </div>

      <div class="form-row second-row">
        <select v-model="form.uf" class="form-input">
          <option value="" disabled>UF</option>
          <option v-for="uf in estados" :key="uf.sigla" :value="uf.sigla">
            {{ uf.sigla }} - {{ uf.nome }}
          </option>
        </select>
        <CampoTexto v-model="form.cidade" placeholder="Cidade" />
        <CampoTexto v-model="form.localidade" placeholder="Localidade" />
      </div>

      <p class="preview-label">Exemplo de visualização na relação de propriedades:</p>

      <div class="preview-row">
        <span>{{ form.nome || 'Fazenda exemplo' }}</span>
        <span>{{ form.proprietario || 'Proprietário' }}</span>
        <span>{{ form.telefone || '(12) 34567-8909' }}</span>
        <span>{{ form.uf || 'RS' }}</span>
        <span>{{ form.cidade || 'Santa Maria' }}</span>
        <span>{{ form.localidade || 'Sede' }}</span>
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
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageCard from '@/components/ui/PageCard.vue'
import CampoTexto from '@/components/ui/CampoTexto.vue'
import Botao from '@/components/ui/Botao.vue'
import { propriedadesAPI } from '@/services/api'

const router = useRouter()
const erro = ref('')
const mensagem = ref('')

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
  nome: '',
  proprietario: '',
  telefone: '',
  uf: '',
  cidade: '',
  localidade: '',
})

async function handleSubmit() {
  erro.value = ''
  mensagem.value = ''

  try {
    await propriedadesAPI.criar({
      nome: form.nome.trim(),
      proprietario: form.proprietario.trim(),
      telefone: form.telefone.trim(),
      uf: form.uf.trim(),
      cidade: form.cidade.trim(),
      localidade: form.localidade.trim(),
    })

    mensagem.value = 'Propriedade salva com sucesso.'
    setTimeout(() => router.push('/propriedades'), 500)
  } catch (error) {
    const detail = error.response?.data
    const message = detail?.detail || 'Não foi possível salvar a propriedade.'
    erro.value = message
    console.error('Erro ao criar propriedade:', error)
  }
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
  background: rgba(180, 62, 62, 0.12);
  color: #7a1d1d;
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