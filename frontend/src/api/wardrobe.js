import api from './axios.js'

export const getItems = () =>
  api.get('/wardrobe/items').then(r => r.data)

export const uploadItem = (formData) =>
  api.post('/wardrobe/items', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)

export const deleteItem = (id) =>
  api.delete(`/wardrobe/items/${id}`).then(r => r.data)

export const patchItem = (id, data) =>
  api.patch(`/wardrobe/items/${id}`, data).then(r => r.data)

export const getWardrobeStats = () =>
  api.get('/wardrobe/stats').then(r => r.data)

export const getImageUrl = (filename) =>
  `${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/uploads/${filename}`
