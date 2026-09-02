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
        Entre na sua conta
      </p>

      <form @submit.prevent="login">

        <input
          v-model="email"
          type="email"
          placeholder="email"
        >

        <input
          v-model="password"
          type="password"
          placeholder="password"
        >

        <p v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </p>

        <button type="submit" :disabled="loading">
          {{ loading ? 'Entrando...' : 'Entrar' }}
        </button>

      </form>

      <a href="#" class="forgot">
        Esqueceu sua Senha?
      </a>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { autenticacaoAPI } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')

const router = useRouter()
const authStore = useAuthStore()

async function login() {
  if (!email.value || !password.value) {
    errorMessage.value = 'Informe e-mail e senha.'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const response = await autenticacaoAPI.login(email.value, password.value)
    const { access, refresh, usuario } = response.data || {}

    if (access) {
      authStore.setToken(access)
    }

    if (refresh) {
      localStorage.setItem('auth_refresh_token', refresh)
    }

    if (usuario) {
      authStore.setUser(usuario)
    } else {
      await authStore.fetchProfile()
    }

    router.push('/home')
  } catch (error) {
    const detail = error.response?.data?.detail
    const nonFieldErrors = error.response?.data?.non_field_errors

    errorMessage.value = detail || nonFieldErrors?.[0] || 'E-mail ou senha inválidos.'
  } finally {
    loading.value = false
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

.forgot {
  display: block;

  margin-top: var(--space-md);

  text-align: center;

  color: var(--text);

  text-decoration: none;

  font-size: .9rem;
}
</style>