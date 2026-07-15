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

      <form @submit.prevent="login">

        <div class="input-row">
          <input placeholder="Nome" v-model="nome">
          <input placeholder="Sobrenome">
          <input placeholder="Estado">
          <input placeholder="Cidade">
        </div>

        <div class="input-row">
          <input placeholder="Email">
          <input placeholder="Celular">
          <input placeholder="Senha">
          <input placeholder="Confirmar Senha">
        </div>

        <div class="checkbox-group">
          <label class="checkbox-item">
            <input
              type="checkbox"
              v-model="consideraImportante"
            >
            <span>
              Considera importante um software para formulação de rações e planejamento na ovinocultura?
            </span>
          </label>

          <label class="checkbox-item">
            <input
              type="checkbox"
              v-model="produtorOvinos"
            >
            <span>
              É produtor de ovinos?
            </span>
          </label>

          <label class="checkbox-item">
            <input
              type="checkbox"
              v-model="aceitaTermos"
              required
            >
            <span>
              Declaro que li e aceito os Termos de Uso
            </span>
          </label>
        </div>
      
        <button type="submit">
          Cadastrar
        </button>

      </form>


    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const email = ref('')
const password = ref('')
const nome = ref('')
const sobrenome = ref('')
const estado = ref('')
const cidade = ref('')


function login() {
  console.log({
    email: email.value,
    password: password.value,
    nome: nome.value,
    sobrenome: sobrenome.value,
    estado: estado.value,
    cidade: cidade.value
  })
}

const consideraImportante = ref(false)
const produtorOvinos = ref(false)
const aceitaTermos = ref(false)
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

.forgot {
  display: block;

  margin-top: var(--space-md);

  text-align: center;

  color: var(--text);

  text-decoration: none;

  font-size: .9rem;
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