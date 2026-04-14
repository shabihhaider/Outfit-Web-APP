import api from './axios.js'

export const getPlans = (month) =>
  api.get(`/calendar/plans?month=${month}`).then(r => r.data)

export const getPlansByRange = (start, end) =>
  api.get('/calendar/plans', { params: { start, end } }).then(r => r.data)

export const createPlan = (data) =>
  api.post('/calendar/plans', data).then(r => r.data)

export const updatePlan = (id, data) =>
  api.patch(`/calendar/plans/${id}`, data).then(r => r.data)

export const deletePlan = (id) =>
  api.delete(`/calendar/plans/${id}`).then(r => r.data)
