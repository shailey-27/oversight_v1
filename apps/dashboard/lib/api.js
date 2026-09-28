import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 15000,
})

// Auto-attach JWT token to every request
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-handle 401 → redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.clear()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────────────
export const sendOTP = (phone) => api.post('/auth/send-otp', { phone })
export const verifyOTP = (phone, otp) => api.post('/auth/verify-otp', { phone, otp })
export const registerUser = (data) => api.post('/auth/register', data)
export const getMe = () => api.get('/auth/me')

// ── Dashboard / Analytics ─────────────────────────────────────
export const getDashboardOverview = () => api.get('/analytics/dashboard-overview')
export const getPriorityScore = (id) => api.get(`/analytics/priority-score/${id}`)
export const computeScore = (id) => api.post(`/analytics/compute-score/${id}`)

// ── Institutions ──────────────────────────────────────────────
export const getInstitutions = () => api.get('/institutions/')
export const getInstitution = (id) => api.get(`/institutions/${id}`)
export const createInstitution = (data) => api.post('/institutions/', data)

// ── Inspections ───────────────────────────────────────────────
export const getMyInspections = () => api.get('/inspections/my-inspections')
export const getInspection = (id) => api.get(`/inspections/${id}`)
export const assignInspection = (data) => api.post('/inspections/assign', data)
export const submitInspection = (id, data) => api.post(`/inspections/${id}/submit`, data)

// ── Video Calls ───────────────────────────────────────────────
export const initiateVideoCall = (data) => api.post('/video-calls/initiate', data)
export const getCallStatus = (id) => api.get(`/video-calls/${id}`)
export const recordNoShow = (id) => api.post(`/video-calls/${id}/no-show`)

export default api
