import axios from 'axios'

function resolveApiBaseUrl(): string {
  const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL
  const normalizedBaseUrl = configuredBaseUrl?.trim()

  if (normalizedBaseUrl) {
    return normalizedBaseUrl.replace(/\/+$/, '')
  }

  return 'http://127.0.0.1:8888'
}

export const apiClient = axios.create({
  baseURL: resolveApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
})
