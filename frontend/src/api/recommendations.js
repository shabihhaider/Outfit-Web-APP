import api from './axios.js'

export const getRecommendations = (data) =>
  api.post('/recommendations', data).then(r => r.data)

export const getAroundItem = (itemId, data) =>
  api.post(`/recommendations/around-item/${itemId}`, data).then(r => r.data)

export const getOOTD = (tempCelsius) =>
  api.get('/recommendations/ootd', { params: tempCelsius != null ? { temp_celsius: tempCelsius } : {} }).then(r => r.data)

export const scoreOutfit = (data) =>
  api.post('/recommendations/score-outfit', data).then(r => r.data)
