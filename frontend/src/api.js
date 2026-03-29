import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const getAccounts    = ()            => api.get('/auth/accounts').then(r => r.data)
export const disconnectAcct = (id)          => api.delete(`/auth/accounts/${id}`)
export const getPosts       = ()            => api.get('/posts').then(r => r.data)
export const getPostStatus  = (id)          => api.get(`/posts/${id}`).then(r => r.data)
export const cancelPost     = (id)          => api.delete(`/posts/${id}`)
export const getVideos      = (channelId)   => api.get(`/youtube/${channelId}/videos`).then(r => r.data)

export const uploadPost = (formData) =>
  api.post('/posts/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)

export default api
