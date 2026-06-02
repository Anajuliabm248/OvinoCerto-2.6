import { defineStore } from 'pinia'
import { ref } from 'vue'
import { propriedadesAPI } from '../services/api'

export const usePropriedadesStore = defineStore('propriedades', () => {
  const propriedades = ref([])
  const loading = ref(false)
  const error = ref(null)

  const listar = async (params = {}) => {
    loading.value = true
    error.value = null
    try {
      const response = await propriedadesAPI.listar(params)
      propriedades.value = response.data.results || response.data
      return propriedades.value
    } catch (err) {
      error.value = err.message
      console.error('Erro ao listar propriedades:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const obter = async (id) => {
    try {
      const response = await propriedadesAPI.obter(id)
      return response.data
    } catch (err) {
      console.error('Erro ao obter propriedade:', err)
      throw err
    }
  }

  const criar = async (data) => {
    try {
      const response = await propriedadesAPI.criar(data)
      propriedades.value.push(response.data)
      return response.data
    } catch (err) {
      console.error('Erro ao criar propriedade:', err)
      throw err
    }
  }

  const atualizar = async (id, data) => {
    try {
      const response = await propriedadesAPI.atualizar(id, data)
      const index = propriedades.value.findIndex((p) => p.id === id)
      if (index !== -1) {
        propriedades.value[index] = response.data
      }
      return response.data
    } catch (err) {
      console.error('Erro ao atualizar propriedade:', err)
      throw err
    }
  }

  const deletar = async (id) => {
    try {
      await propriedadesAPI.deletar(id)
      propriedades.value = propriedades.value.filter((p) => p.id !== id)
    } catch (err) {
      console.error('Erro ao deletar propriedade:', err)
      throw err
    }
  }

  return {
    propriedades,
    loading,
    error,
    listar,
    obter,
    criar,
    atualizar,
    deletar,
  }
})
