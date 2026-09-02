import axios from 'axios'

const API_URL = 'http://localhost:8000/api'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptador para adicionar token em cada requisição
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Interceptador para tratar erros
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const url = error.config?.url || ''
      const isPublicReadRequest =
        url.includes('/ingredientes') ||
        url.includes('/exigencias') ||
        url.includes('/formulacoes')

      if (!isPublicReadRequest) {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('user')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// === USUÁRIOS ===
export const usuariosAPI = {
  listar: (params = {}) => api.get('/usuarios/', { params }),
  obter: (id) => api.get(`/usuarios/${id}/`),
  criar: (data) => api.post('/usuarios/', data),
  atualizar: (id, data) => api.put(`/usuarios/${id}/`, data),
  deletar: (id) => api.delete(`/usuarios/${id}/`),
  meuPerfil: () => api.get('/usuarios/me/'),
}

// === PROPRIEDADES ===
export const propriedadesAPI = {
  listar: (params = {}) => api.get('/propriedades/', { params }),
  obter: (id) => api.get(`/propriedades/${id}/`),
  criar: (data) => api.post('/propriedades/', data),
  atualizar: (id, data) => api.put(`/propriedades/${id}/`, data),
  deletar: (id) => api.delete(`/propriedades/${id}/`),
}

// === LOTES ===
export const lotesAPI = {
  listar: (params = {}) => api.get('/lotes/', { params }),
  obter: (id) => api.get(`/lotes/${id}/`),
  criar: (data) => api.post('/lotes/', data),
  atualizar: (id, data) => api.put(`/lotes/${id}/`, data),
  deletar: (id) => api.delete(`/lotes/${id}/`),
}

// === EXIGÊNCIAS NRC ===
export const exigenciasAPI = {
  listar: (params = {}) => api.get('/exigencias/', { params }),
  obter: (id) => api.get(`/exigencias/${id}/`),
}

// === INGREDIENTES ===
export const ingredientesAPI = {
  listar: (params = {}) => api.get('/ingredientes/', { params }),
  obter: (id) => api.get(`/ingredientes/${id}/`),
  criar: (data) => api.post('/ingredientes/', data),
  atualizar: (id, data) => api.put(`/ingredientes/${id}/`, data),
  atualizarParcial: (id, data) => api.patch(`/ingredientes/${id}/`, data),
  deletar: (id) => api.delete(`/ingredientes/${id}/`),
  meus: () => api.get('/ingredientes/meus/'),
  tipos: () => api.get('/ingredientes/tipos/'),
  atualizarPreco: (id, preco) => api.patch(`/ingredientes/${id}/preco/`, { preco }),
}

// === AUTENTICAÇÃO ===
export const autenticacaoAPI = {
  login: (username, password) =>
    api.post('/api-token-auth/', { username, password }),
  logout: () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')
  },
}

export default api