import api from './axios.js'

export const getPersonPhoto = () =>
  api.get('/vto/person-photo').then(r => r.data)

export const uploadPersonPhoto = (formData) =>
  api.post('/vto/person-photo', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)

export const submitTryOn = (itemId) =>
  api.post('/vto/jobs', { item_id: itemId }).then(r => r.data)

export const getJobStatus = (jobId) =>
  api.get(`/vto/jobs/${jobId}`).then(r => r.data)
