import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { usuariosAPI } from '../services/api'

const readStoredUser = () => {
  try {
    const raw = localStorage.getItem('user')
    return raw ? JSON.parse(raw) : null
  } catch (error) {
    console.warn('Não foi possível restaurar o usuário salvo:', error)
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref(readStoredUser())
  const token = ref(localStorage.getItem('auth_token') || null)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => {
    const perfil = user.value?.perfil
    return !!(
      perfil === 'ADMIN' ||
      user.value?.is_admin ||
      user.value?.pode_gerenciar_usuarios
    )
  })

  const canManageUsers = computed(() => {
    const perfil = user.value?.perfil
    return !!(
      perfil === 'ADMIN' ||
      user.value?.pode_gerenciar_usuarios ||
      user.value?.is_admin
    )
  })

  const setUser = (newUser) => {
    user.value = newUser
    if (newUser) {
      localStorage.setItem('user', JSON.stringify(newUser))
    } else {
      localStorage.removeItem('user')
    }
  }

  const setToken = (newToken) => {
    token.value = newToken
    if (newToken) {
      localStorage.setItem('auth_token', newToken)
    } else {
      localStorage.removeItem('auth_token')
    }
  }

  const fetchProfile = async () => {
    try {
      const response = await usuariosAPI.meuPerfil()
      const profile = response?.data || null
      if (profile) {
        setUser(profile)
      }
      return profile
    } catch (error) {
      if (error.response?.status === 404) {
        setUser(null)
        return null
      }

      console.error('Erro ao buscar perfil:', error)
      throw error
    }
  }

  const logout = () => {
    user.value = null
    token.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_refresh_token')
    localStorage.removeItem('user')
  }

  return {
    user,
    token,
    isAuthenticated,
    isAdmin,
    canManageUsers,
    setUser,
    setToken,
    fetchProfile,
    logout,
  }
})
