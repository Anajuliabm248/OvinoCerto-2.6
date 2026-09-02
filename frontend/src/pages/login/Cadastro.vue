<template>
  <div class="login-page">
    <div class="login-card">

      <div class="logo-container">
        <img
          src="@/assets/logo_preta_2.png"
          alt="OvinoCerto"
          class="logo"
        >

        <h1>
          Ovino<span>Certo</span>
          <small>2.6</small>
        </h1>
      </div>

      <p class="subtitle">
        Crie sua conta
      </p>

      <form @submit.prevent="cadastrar">
        <div class="input-row">
          <input v-model="nome" placeholder="Nome completo">
          <input v-model="cpf" placeholder="CPF">
          <input v-model="estado" placeholder="Estado">
          <input v-model="cidade" placeholder="Cidade">
        </div>

        <div class="input-row">
          <input v-model="email" placeholder="Email" type="email">
          <input v-model="telefone" placeholder="Telefone">
          <input v-model="profissao" placeholder="Profissão">
        </div>

        <div class="input-row password-row">
          <input v-model="password" placeholder="Senha" type="password">
          <input v-model="password2" placeholder="Confirmar Senha" type="password">
        </div>

        <div class="checkbox-group">
          <label class="checkbox-item">
            <input type="checkbox" v-model="consideraImportante">
            <span>
              Considera importante um software para formulação de rações e planejamento na ovinocultura?
            </span>
          </label>

          <label class="checkbox-item">
            <input type="checkbox" v-model="produtorOvinos">
            <span>
              É produtor de ovinos?
            </span>
          </label>

          <label class="checkbox-item">
            <input type="checkbox" v-model="aceitaTermos" required>
            <span>
              Declaro que li e aceito os Termos de Uso
            </span>
          </label>
        </div>

        <p v-if="erroMensagem" class="erro-mensagem">
          {{ erroMensagem }}
        </p>

        <button type="submit" :disabled="carregando">
          {{ carregando ? 'Cadastrando...' : 'Cadastrar' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { autenticacaoAPI } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const password2 = ref('')
const nome = ref('')
const cpf = ref('')
const estado = ref('')
const cidade = ref('')
const telefone = ref('')
const profissao = ref('')
const carregando = ref(false)
const erroMensagem = ref('')

const consideraImportante = ref(false)
const produtorOvinos = ref(false)
const aceitaTermos = ref(false)

async function cadastrar() {
  if (!nome.value || !cpf.value || !email.value || !telefone.value || !estado.value || !cidade.value || !profissao.value) {
    erroMensagem.value = 'Preencha todos os campos do perfil: nome completo, CPF, email, telefone, estado, cidade e profissão.'
    return
  }

  if (!password.value || !password2.value) {
    erroMensagem.value = 'Preencha a senha e a confirmação.'
    return
  }

  if (password.value !== password2.value) {
    erroMensagem.value = 'As senhas não coincidem.'
    return
  }

  if (!aceitaTermos.value) {
    erroMensagem.value = 'Você precisa aceitar os termos para continuar.'
    return
  }

  carregando.value = true
  erroMensagem.value = ''

  try {
    const payload = {
      nome: nome.value.trim(),
      email: email.value.trim(),
      cpf: cpf.value.trim(),
      telefone: telefone.value.trim(),
      estado: estado.value.trim(),
      cidade: cidade.value.trim(),
      profissao: profissao.value.trim(),
      produtor_ovinos: produtorOvinos.value,
      password: password.value,
      password2: password2.value,
    }

    const response = await autenticacaoAPI.register(payload)
    const { access, refresh, usuario } = response.data || {}

    if (access) {
      authStore.setToken(access)
    }

    if (refresh) {
      localStorage.setItem('auth_refresh_token', refresh)
    }

    if (usuario) {
      authStore.setUser(usuario)
    }

    await authStore.fetchProfile()
    router.push('/home')
  } catch (error) {
    console.error('Erro ao cadastrar:', error)
    const detail = error.response?.data?.detail
    const nonFieldErrors = error.response?.data?.non_field_errors
    const erros = error.response?.data

    if (erros && typeof erros === 'object') {
      const primeiroErro = Object.values(erros).flat().find(Boolean)
      erroMensagem.value = primeiroErro || 'Não foi possível concluir o cadastro.'
      return
    }

    erroMensagem.value = detail || nonFieldErrors?.[0] || 'Não foi possível concluir o cadastro.'
  } finally {
    carregando.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;

  background: var(--primary);
}

.login-card {
  width: 500px;

  background: var(--background);

  padding: 48px;

  border-radius: 24px;

  box-shadow:
    0 8px 20px rgba(0,0,0,.15);
}

.logo-container {
  display: flex;
  align-items: center;
  justify-content: center;

  gap: var(--space-xs);

  margin-bottom: var(--space-md);
}

.logo {
  width: 52px;
  height: 52px;
}

.logo-container h1 {
  margin: 0;
  margin-top: 6px;

  font-size: 2.5rem;
  font-weight: 300;

  color: var(--text);
}

.logo-container span {
  font-weight: 700;
}

.logo-container small {
  font-size: 1.3rem;
  margin-left: 4px;
}

.subtitle {
  text-align: center;

  color: var(--text);

  margin-bottom: var(--space-lg);
}

form {
  display: flex;
  flex-direction: column;

  gap: var(--space-sm);
}

* {
  box-sizing: border-box;
}

input {
  height: 48px;

  border: 1px solid var(--border);

  border-radius: var(--radius-sm);

  padding: 0 16px;

  background: #CFC6B5;

  font-size: 1rem;

  outline: none;
}

input:focus {
  border-color: var(--primary-dark);
}

.input-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-xxs);
  width: 100%;
}

.password-row {
  grid-template-columns: repeat(2, 1fr);
}

.input-row input {
  width: 100%;
  box-sizing: border-box;
}

button {
  width: 180px;
  height: 48px;

  margin: 8px auto 0;

  border: none;
  border-radius: var(--radius-sm);

  background: var(--primary-dark);

  color: white;

  font-weight: 600;

  cursor: pointer;

  transition: .2s;
}

button:hover {
  transform: translateY(-1px);
}

.erro-mensagem {
  margin: 0;
  color: #b42318;
  font-size: 0.9rem;
  font-weight: 600;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);

  margin-top: var(--space-md);
  margin-bottom: var(--space-sm);
  margin-left: 8px;
  margin-right: 4px;
}

.checkbox-item {
  display: flex;
  flex-direction: row-reverse;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-xs);

  color: var(--text);
  font-size: 14px;

  cursor: pointer;
}

.checkbox-item input[type="checkbox"] {
  margin-top: 2px;
  min-width: 18px;
  min-height: 18px;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  accent-color: var(--primary);
}
</style>