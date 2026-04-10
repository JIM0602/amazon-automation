import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import api from '../api/client'
import type { User, UserRole } from '../types'

interface AuthContextType {
  user: User | null
  role: UserRole | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [role, setRole] = useState<UserRole | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        setUser({ username: payload.sub, role: payload.role as UserRole })
        setRole(payload.role as UserRole)
      } catch (error) {
        console.error('Invalid token', error)
        localStorage.removeItem('token')
        localStorage.removeItem('refresh_token')
      }
    }
    setLoading(false)
  }, [])

  const login = async (username: string, password: string) => {
    try {
      const response = await api.post('/auth/login', { username, password })
      const { access_token, refresh_token } = response.data
      
      localStorage.setItem('token', access_token)
      localStorage.setItem('refresh_token', refresh_token)
      
      const payload = JSON.parse(atob(access_token.split('.')[1]))
      setUser({ username: payload.sub, role: payload.role as UserRole })
      setRole(payload.role as UserRole)
    } catch (error) {
      console.error('Login failed', error)
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    setUser(null)
    setRole(null)
  }

  return (
    <AuthContext.Provider value={{ user, role, isAuthenticated: !!user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}