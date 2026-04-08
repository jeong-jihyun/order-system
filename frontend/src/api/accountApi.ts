import { apiClient } from './axiosConfig'

export interface AccountResponse {
  id: number
  accountNumber: string
  accountType: string
  balance: number
  frozenBalance: number
  availableBalance: number
  active: boolean
  createdAt: string
}

export interface BalanceRequest {
  amount: number
}

export interface CreateAccountRequest {
  accountType: 'CASH' | 'STOCK' | 'DERIVATIVE'
}

interface ApiResponse<T> {
  success: boolean
  message: string
  data: T
}

const BASE = '/api/v1/accounts'

export const accountApi = {
  getMyAccounts: async (): Promise<AccountResponse[]> => {
    const res = await apiClient.get<ApiResponse<AccountResponse[]>>(`${BASE}/me`)
    return res.data.data
  },

  getById: async (id: number): Promise<AccountResponse> => {
    const res = await apiClient.get<ApiResponse<AccountResponse>>(`${BASE}/${id}`)
    return res.data.data
  },

  deposit: async (id: number, amount: number): Promise<AccountResponse> => {
    const res = await apiClient.post<ApiResponse<AccountResponse>>(
      `${BASE}/${id}/deposit`,
      { amount },
    )
    return res.data.data
  },

  withdraw: async (id: number, amount: number): Promise<AccountResponse> => {
    const res = await apiClient.post<ApiResponse<AccountResponse>>(
      `${BASE}/${id}/withdraw`,
      { amount },
    )
    return res.data.data
  },

  create: async (accountType: CreateAccountRequest['accountType']): Promise<AccountResponse> => {
    const res = await apiClient.post<ApiResponse<AccountResponse>>(BASE, { accountType })
    return res.data.data
  },
}
