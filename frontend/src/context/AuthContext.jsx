import { createContext, useContext, useState, useCallback } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('outfit_token'))
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('outfit_user') || 'null')
    } catch {
      return null
    }
  })

  const loginUser = useCallback((accessToken, userData) => {
    localStorage.setItem('outfit_token', accessToken)
    localStorage.setItem('outfit_user', JSON.stringify(userData))
    setToken(accessToken)
    setUser(userData)
  }, [])

  const logoutUser = useCallback(() => {
    localStorage.removeItem('outfit_token')
    localStorage.removeItem('outfit_user')
    setToken(null)
    setUser(null)
  }, [])

  const updateUser = useCallback((partial) => {
    setUser(prev => {
      const next = { ...prev, ...partial }
      localStorage.setItem('outfit_user', JSON.stringify(next))
      return next
    })
  }, [])

  const isAuthenticated = Boolean(token)

  return (
    <AuthContext.Provider value={{ token, user, isAuthenticated, loginUser, logoutUser, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
