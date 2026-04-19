const API_URL = import.meta.env.VITE_API_URL || ''

export const resolveUrl = (url) => {
  if (!url) return null
  if (url.startsWith('http')) return url
  // Append JWT so the authenticated /uploads/ endpoint accepts <img src> requests
  const token = localStorage.getItem('outfit_token')
  const sep = url.includes('?') ? '&' : '?'
  return `${API_URL}${url}${token ? `${sep}token=${encodeURIComponent(token)}` : ''}`
}
