import { create } from 'zustand'
import axios from 'axios'

// API directe (pas via l'instance avec interceptors pour eviter boucle redirect)
const authApi = axios.create({ baseURL: '' })

export const useAuthStore = create((set) => ({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  token: localStorage.getItem('token') || null,

  login: async (pin) => {
    const { data } = await authApi.post('/api/auth/login', { pin })
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.utilisateur))
    set({ user: data.utilisateur, token: data.access_token })
    return data.utilisateur
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ user: null, token: null })
  },
}))
