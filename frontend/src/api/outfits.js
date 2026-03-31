import api from './axios.js'

export const saveOutfit = (data) =>
  api.post('/outfits/saved', data).then(r => r.data)

export const getSaved = () =>
  api.get('/outfits/saved').then(r => r.data)

export const deleteSaved = (id) =>
  api.delete(`/outfits/saved/${id}`).then(r => r.data)

export const getHistory = () =>
  api.get('/outfits/history').then(r => r.data)

export const submitFeedback = (historyId, data) =>
  api.post(`/outfits/${historyId}/feedback`, data).then(r => r.data)
