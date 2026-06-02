import { defineStore } from 'pinia'
import { ref } from 'vue'
import { lotesAPI } from '../services/api'

export const useLotesStore = defineStore('lotes', () => {
  const lotes = ref([])
  const loading = ref(false)
  const error = ref(null)

  const listar = async (params = {}) => {
    loading.value = true
    error.value = null
    try {
      const response = await lotesAPI.listar(params)
      lotes.value = response.data.results || response.data
      return lotes.value
    } catch (err) {
      error.value = err.message
      console.error('Erro ao listar lotes:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const obter = async (id) => {
    try {
      const response = await lotesAPI.obter(id)
      return response.data
    } catch (err) {
      console.error('Erro ao obter lote:', err)
      throw err
    }
  }

  const criar = async (data) => {
    try {
      const response = await lotesAPI.criar(data)
      lotes.value.push(response.data)
      return response.data
    } catch (err) {
      console.error('Erro ao criar lote:', err)
      throw err
    }
  }

  const atualizar = async (id, data) => {
    try {
      const response = await lotesAPI.atualizar(id, data)
      const index = lotes.value.findIndex((l) => l.id === id)
      if (index !== -1) {
        lotes.value[index] = response.data
      }
      return response.data
    } catch (err) {
      console.error('Erro ao atualizar lote:', err)
      throw err
    }
  }

  const deletar = async (id) => {
    try {
      await lotesAPI.deletar(id)
      lotes.value = lotes.value.filter((l) => l.id !== id)
    } catch (err) {
      console.error('Erro ao deletar lote:', err)
      throw err
    }
  }

  return {
    lotes,
    loading,
    error,
    listar,
    obter,
    criar,
    atualizar,
    deletar,
  }
})
