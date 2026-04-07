import api from './axios.js'

export const register = (data) =>
  api.post('/auth/register', data).then(r => r.data)

export const login = (data) =>
  api.post('/auth/login', data).then(r => r.data)

export const refreshToken = () =>
  api.post('/auth/refresh').then(r => r.data)

export const getConsent = () =>
  api.get('/auth/consent').then(r => r.data)

export const updateConsent = (data) =>
  api.patch('/auth/consent', data).then(r => r.data)

export const getPrivacySummary = () =>
  api.get('/auth/privacy-summary').then(r => r.data)

export const exportData = () =>
  api.get('/auth/data-export').then(r => r.data)

export const deleteAccount = (data) =>
  api.delete('/auth/account', { data }).then(r => r.data)

export const changePassword = (data) =>
  api.post('/auth/change-password', data).then(r => r.data)
