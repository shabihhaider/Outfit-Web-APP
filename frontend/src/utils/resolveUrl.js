const API_URL = import.meta.env.VITE_API_URL || ''

export const resolveUrl = (url) => {
  if (!url) return null
  if (url.startsWith('http')) return url
  return `${API_URL}${url}`
}
