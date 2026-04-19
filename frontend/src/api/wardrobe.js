import api from './axios.js'

export const getItems = ({ page = 1, limit = 20, category } = {}) => {
  const params = { page, limit }
  if (category && category !== 'all') params.category = category
  return api.get('/wardrobe/items', { params }).then(r => r.data)
}

export const uploadItem = (formData) =>
  api.post('/wardrobe/items', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)

export const deleteItem = (id) =>
  api.delete(`/wardrobe/items/${id}`).then(r => r.data)

export const patchItem = (id, data) =>
  api.patch(`/wardrobe/items/${id}`, data).then(r => r.data)

export const bulkDeleteItems = (item_ids) =>
  api.delete('/wardrobe/items/bulk', { data: { item_ids } }).then(r => r.data)

export const bulkUpdateFormality = (item_ids, formality) =>
  api.patch('/wardrobe/items/bulk', { item_ids, formality }).then(r => r.data)

export const getWardrobeStats = () =>
  api.get('/wardrobe/stats').then(r => r.data)

export const getImageUrl = (filename) => {
  if (!filename) return null
  if (filename.startsWith('http')) return filename
  return `${import.meta.env.VITE_API_URL || ''}/uploads/${filename}`
}
