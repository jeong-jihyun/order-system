import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { authApi, LoginResponse } from '@/api/authApi'

const TOKEN_KEY = 'auth_token'
const USER_KEY = 'auth_user'

interface AuthUser {
  userId: number
  username: string
  role: string
}

interface AuthContextValue {
  user: AuthUser | null
  isLoggedIn: boolean
  login: (data: LoginResponse) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const loadUser = (): AuthUser | null => {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(loadUser)

  const login = useCallback((data: LoginResponse) => {
    localStorage.setItem(TOKEN_KEY, data.accessToken)
    const userInfo: AuthUser = {
      userId: data.userId,
      username: data.username,
      role: data.role,
    }
    localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
    setUser(userInfo)
  }, [])

  const logout = useCallback(() => {
    authApi.removeToken()
    localStorage.removeItem(USER_KEY)
    setUser(null)
    window.location.href = '/login'
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoggedIn: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
