import api from './axios.js'

export const getNotifications      = (params) => api.get('/social/notifications', { params }).then(r => r.data)
export const getNotificationCount  = ()        => api.get('/social/notifications/count').then(r => r.data)
export const markAllRead           = ()        => api.post('/social/notifications/read-all').then(r => r.data)
export const getTodayPlan          = ()        => api.get('/calendar/plans/today').then(r => r.data)
