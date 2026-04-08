import { apiClient } from './axiosConfig'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  accessToken: string
  tokenType: string
  userId: number
  username: string
  role: string
  expiresIn: number
}

export interface SignupRequest {
  username: string
  password: string
  email: string
  fullName: string
}

const AUTH_TOKEN_KEY = 'auth_token'

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const res = await apiClient.post<{ success: boolean; data: LoginResponse }>(
      '/api/v1/auth/login',
      data,
    )
    return res.data.data
  },

  signup: async (data: SignupRequest): Promise<LoginResponse> => {
    const res = await apiClient.post<{ success: boolean; data: LoginResponse }>(
      '/api/v1/auth/signup',
      data,
    )
    return res.data.data
  },

  saveToken: (token: string) => localStorage.setItem(AUTH_TOKEN_KEY, token),
  getToken: () => localStorage.getItem(AUTH_TOKEN_KEY),
  removeToken: () => localStorage.removeItem(AUTH_TOKEN_KEY),
  isLoggedIn: () => !!localStorage.getItem(AUTH_TOKEN_KEY),
}
