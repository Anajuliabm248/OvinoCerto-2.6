<template>
  <div>
    <Header theme="dark" />
    <div class="perfil-page">
      <div class="perfil-card">
      <h1 class="titulo">Minha Conta</h1>

      <div class="campo-linha">
        <span class="campo-label">Nome:</span>
        <span class="campo-valor">{{ nome || 'Usuário' }}</span>
      </div>

      <div class="campo-linha">
        <span class="campo-label">CPF:</span>
        <span class="campo-valor">{{ cpf || 'Não informado' }}</span>
      </div>

      <form class="perfil-form" @submit.prevent="salvarDados">
        <div class="campo-edicao">
          <div class="campo-texto">
            <label class="campo-label">E-mail:</label>
          </div>
          <div class="campo-valor-wrapper">
            <div class="campo-valor-editavel">
              <span v-if="!modoEdicao">{{ email || 'Não informado' }}</span>
              <input v-else v-model="email" placeholder="E-mail" type="email">
            </div>
            <Botao
              :label="modoEdicao ? 'Cancelar' : 'Alterar'"
              :variant="modoEdicao ? 'outline' : 'primary'"
              @click="toggleEdicao"
            />
          </div>
        </div>

        <div class="campo-edicao">
          <div class="campo-texto">
            <label class="campo-label">Telefone:</label>
          </div>
          <div class="campo-valor-wrapper">
            <div class="campo-valor-editavel">
              <span v-if="!modoEdicao">{{ telefone || 'Não informado' }}</span>
              <input v-else v-model="telefone" placeholder="Telefone">
            </div>
            <Botao
              :label="modoEdicao ? 'Cancelar' : 'Alterar'"
              :variant="modoEdicao ? 'outline' : 'primary'"
              @click="toggleEdicao"
            />
          </div>
        </div>

        <div class="campo-edicao">
          <div class="campo-texto">
            <label class="campo-label">Estado:</label>
          </div>
          <div class="campo-valor-wrapper">
            <div class="campo-valor-editavel">
              <span v-if="!modoEdicao">{{ estado || 'Não informado' }}</span>
              <input v-else v-model="estado" placeholder="Estado">
            </div>
            <Botao
              :label="modoEdicao ? 'Cancelar' : 'Alterar'"
              :variant="modoEdicao ? 'outline' : 'primary'"
              @click="toggleEdicao"
            />
          </div>
        </div>

        <div class="campo-edicao">
          <div class="campo-texto">
            <label class="campo-label">Cidade:</label>
          </div>
          <div class="campo-valor-wrapper">
            <div class="campo-valor-editavel">
              <span v-if="!modoEdicao">{{ cidade || 'Não informado' }}</span>
              <input v-else v-model="cidade" placeholder="Cidade">
            </div>
            <Botao
              :label="modoEdicao ? 'Cancelar' : 'Alterar'"
              :variant="modoEdicao ? 'outline' : 'primary'"
              @click="toggleEdicao"
            />
          </div>
        </div>

        <div class="campo-edicao">
          <div class="campo-texto">
            <label class="campo-label">Profissão:</label>
          </div>
          <div class="campo-valor-wrapper">
            <div class="campo-valor-editavel">
              <span v-if="!modoEdicao">{{ profissao || 'Não informada' }}</span>
              <input v-else v-model="profissao" placeholder="Profissão">
            </div>
            <Botao
              :label="modoEdicao ? 'Cancelar' : 'Alterar'"
              :variant="modoEdicao ? 'outline' : 'primary'"
              @click="toggleEdicao"
            />
          </div>
        </div>
      </form>

      <h2 class="subtitulo">Alteração de senha</h2>

      <form class="senha-form" @submit.prevent="alterarSenha">
        <input v-model="senhaAtual" placeholder="Senha atual" type="password">

        <div class="senha-row">
          <input v-model="novaSenha" placeholder="Nova senha" type="password">
          <input v-model="confirmarSenha" placeholder="Confirmar senha" type="password">
        </div>
      </form>

      <Botao label="Salvar alterações" variant="primary" @click="salvarAlteracoes" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usuariosAPI } from '@/services/api'
import Botao from '@/components/ui/Botao.vue'
import Header from '@/components/layout/Header.vue'

const router = useRouter()
const authStore = useAuthStore()

const nome = ref('')
const cpf = ref('')
const email = ref('')
const telefone = ref('')
const estado = ref('')
const cidade = ref('')
const profissao = ref('')
const modoEdicao = ref(false)

const senhaAtual = ref('')
const novaSenha = ref('')
const confirmarSenha = ref('')

function toggleEdicao() {
  modoEdicao.value = !modoEdicao.value
}

async function carregarPerfil() {
  try {
    const { data } = await usuariosAPI.meuPerfil()
    nome.value = data.nome || ''
    cpf.value = data.cpf || ''
    email.value = data.email || ''
    telefone.value = data.telefone || ''
    estado.value = data.estado || ''
    cidade.value = data.cidade || ''
    profissao.value = data.profissao || ''

    if (data) {
      authStore.setUser(data)
    }
  } catch (error) {
    console.error('Erro ao carregar perfil:', error)

    if (authStore.user) {
      nome.value = authStore.user.nome || ''
      cpf.value = authStore.user.cpf || ''
      email.value = authStore.user.email || ''
      telefone.value = authStore.user.telefone || ''
      estado.value = authStore.user.estado || ''
      cidade.value = authStore.user.cidade || ''
      profissao.value = authStore.user.profissao || ''
      return
    }

    alert('Faça login para acessar sua conta.')
    router.push('/login')
  }
}

async function salvarDados() {
  const usuarioId = authStore.user?.id

  if (!usuarioId) {
    alert('Usuário não autenticado.')
    return
  }

  try {
    await usuariosAPI.atualizarPerfil(usuarioId, {
      nome: nome.value,
      email: email.value,
      telefone: telefone.value,
      estado: estado.value,
      cidade: cidade.value,
      profissao: profissao.value,
    })

    await authStore.fetchProfile()
    alert('Dados salvos com sucesso.')
  } catch (error) {
    console.error('Erro ao atualizar dados:', error)
    alert('Não foi possível salvar os dados do perfil.')
  }
}

async function alterarSenha() {
  if (!senhaAtual.value && !novaSenha.value && !confirmarSenha.value) {
    return
  }

  if (!senhaAtual.value || !novaSenha.value || !confirmarSenha.value) {
    alert('Preencha todos os campos de senha.')
    return
  }

  if (novaSenha.value !== confirmarSenha.value) {
    alert('As senhas não coincidem.')
    return
  }

  alert('A troca de senha ainda não está integrada ao backend. A funcionalidade será concluída na etapa de autenticação avançada.')
  senhaAtual.value = ''
  novaSenha.value = ''
  confirmarSenha.value = ''
}

async function salvarAlteracoes() {
  await salvarDados()

  if (senhaAtual.value || novaSenha.value || confirmarSenha.value) {
    await alterarSenha()
  }
}

onMounted(carregarPerfil)
</script>

<style scoped>
.perfil-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;

  background: var(--primary);
  padding-top: 65px;
}

.perfil-card {
  width: 620px;
  max-width: 92vw;

  background: var(--background);

  padding: 48px;

  border-radius: 24px;

  box-shadow:
    0 8px 20px rgba(0,0,0,.15);
}

* {
  box-sizing: border-box;
}

.titulo {
  text-align: center;

  margin: 0 0 var(--space-lg);

  font-size: 1.6rem;
  font-weight: 700;

  color: var(--text);
}

.subtitulo {
  text-align: center;

  margin: var(--space-lg) 0 var(--space-md);

  font-size: 1.3rem;
  font-weight: 700;

  color: var(--text);
}

.campo-linha {
  display: flex;
  align-items: baseline;
  gap: var(--space-xs);
  margin-bottom: var(--space-sm);
}

.campo-label {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text);
}

.campo-valor {
  font-size: 1rem;
  color: var(--text);
}

.campo-edicao {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  margin-bottom: var(--space-sm);
}

.campo-texto {
  width: 120px;
  flex-shrink: 0;
}

.campo-valor-wrapper {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex: 1;
  margin-left: 12px;
}

.campo-valor-editavel {
  flex: 1;
  min-height: 48px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: #f3efe7;
  color: var(--text);
}

.campo-valor-editavel input {
  width: 100%;
  height: 44px;
  border: none;
  background: transparent;
  padding: 0;
  font-size: 1rem;
  color: var(--text);
  outline: none;
}

.perfil-form,
.senha-form {
  display: flex;
  flex-direction: column;

  gap: var(--space-xs);
}

.senha-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-xs);
}

input {
  width: 100%;
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

.perfil-form {
  margin-top: var(--space-md);
}

:deep(.botao) {
  min-width: 120px;
  padding-inline: 18px;
}

button {
  white-space: nowrap;
}
</style>
