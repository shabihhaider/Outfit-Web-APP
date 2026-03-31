import api from './axios.js'

export const register = (data) =>
  api.post('/auth/register', data).then(r => r.data)

export const login = (data) =>
  api.post('/auth/login', data).then(r => r.data)

export const refreshToken = () =>
  api.post('/auth/refresh').then(r => r.data)
