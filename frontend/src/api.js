import axios from 'axios'

export const api = axios.create({baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api', timeout: 20000})

api.interceptors.request.use(c => {
  const t = localStorage.getItem('sb_token')
  if (t) c.headers.Authorization = `Bearer ${t}`
  return c
})
api.interceptors.response.use(r => r, e => {
  // expired or invalid token on a protected call: send the user back to login
  if (e.response?.status === 401 && !e.config.url.includes('/auth/')) {
    localStorage.removeItem('sb_token'); localStorage.removeItem('sb_user'); location.href = '/login'
  }
  return Promise.reject(e)
})

export const errMsg = e => {
  const d = e.response?.data?.detail
  if (Array.isArray(d)) return d.map(x => x.msg).join('. ')
  return d || (e.response ? 'Something went wrong. Please try again.' : 'Cannot reach the server. Is the backend running?')
}
