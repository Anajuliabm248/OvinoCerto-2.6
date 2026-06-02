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
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
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
