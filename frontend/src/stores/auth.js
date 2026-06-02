import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { usuariosAPI } from '../services/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('auth_token') || null)

  const isAuthenticated = computed(() => !!token.value)

  const setUser = (newUser) => {
    user.value = newUser
    localStorage.setItem('user', JSON.stringify(newUser))
  }

  const setToken = (newToken) => {
    token.value = newToken
    localStorage.setItem('auth_token', newToken)
  }

  const fetchProfile = async () => {
    try {
      const response = await usuariosAPI.meuPerfil()
      setUser(response.data)
      return response.data
    } catch (error) {
      console.error('Erro ao buscar perfil:', error)
      throw error
    }
  }

  const logout = () => {
    user.value = null
    token.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')
  }

  return {
    user,
    token,
    isAuthenticated,
    setUser,
    setToken,
    fetchProfile,
    logout,
  }
})
