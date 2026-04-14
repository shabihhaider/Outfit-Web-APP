import api from './axios.js'

// ── Profile ────────────────────────────────────────────────────────────────
export const getMyProfile     = ()     => api.get('/social/profile').then(r => r.data)
export const updateProfile    = (data) => api.patch('/social/profile', data).then(r => r.data)
export const uploadAvatar     = (file) => {
  const fd = new FormData()
  fd.append('avatar', file)
  return api.post('/social/profile/avatar', fd, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data)
}
export const getMyStyleDNA    = ()     => api.get('/social/profile/style-dna').then(r => r.data)
export const getPublicProfile = (username) => api.get(`/social/users/${username}`).then(r => r.data)
export const getUserStyleDNA  = (username) => api.get(`/social/users/${username}/style-dna`).then(r => r.data)
export const getCompatibility = (username) => api.get(`/social/users/${username}/compatibility`).then(r => r.data)

// ── Follow ─────────────────────────────────────────────────────────────────
export const followUser   = (userId) => api.post(`/social/follow/${userId}`).then(r => r.data)
export const unfollowUser = (userId) => api.delete(`/social/follow/${userId}`).then(r => r.data)
export const getFollowers = (params) => api.get('/social/followers', { params }).then(r => r.data)
export const getFollowing = (params) => api.get('/social/following', { params }).then(r => r.data)

// ── Publishing ─────────────────────────────────────────────────────────────
export const publishOutfit = (data)   => api.post('/social/publish', data).then(r => r.data)
export const getPost       = (postId) => api.get(`/social/posts/${postId}`).then(r => r.data)
export const updatePost    = (postId, data) => api.patch(`/social/posts/${postId}`, data).then(r => r.data)
export const deletePost    = (postId) => api.delete(`/social/posts/${postId}`).then(r => r.data)

// ── Feed ───────────────────────────────────────────────────────────────────
export const getFeed = (params) => api.get('/social/feed', { params }).then(r => r.data)

// ── Post interactions ──────────────────────────────────────────────────────
export const toggleLike     = (postId) => api.post(`/social/posts/${postId}/like`).then(r => r.data)
export const toggleBookmark = (postId) => api.post(`/social/posts/${postId}/bookmark`).then(r => r.data)
export const getBookmarks   = (params) => api.get('/social/bookmarks', { params }).then(r => r.data)

// ── Remix ──────────────────────────────────────────────────────────────────
export const remixPost       = (postId) => api.post(`/social/posts/${postId}/remix`).then(r => r.data)
export const getRemixChain   = (postId) => api.get(`/social/posts/${postId}/remix-chain`).then(r => r.data)

// ── Search ─────────────────────────────────────────────────────────────────
export const searchUsers = (q) => api.get('/social/users/search', { params: { q } }).then(r => r.data)

// ── Vibes ──────────────────────────────────────────────────────────────────
export const getVibes        = ()       => api.get('/social/vibes').then(r => r.data)
export const getTrendingVibes = (params) => api.get('/social/vibes/trending', { params }).then(r => r.data)
