import { apiClient } from './axiosConfig'

export interface SettlementRecord {
  id: number
  orderId: number
  counterOrderId: number
  username: string
  symbol: string
  side: 'BUY' | 'SELL'
  executionPrice: number
  executionQuantity: number
  grossAmount: number
  commission: number
  tax: number
  netAmount: number
  settlementDate: string
  status: string
  executedAt: string
  settledAt: string | null
}

interface ApiResponse<T> {
  success: boolean
  message: string
  data: T
}

export const settlementApi = {
  getMySettlements: async (): Promise<SettlementRecord[]> => {
    const res = await apiClient.get<ApiResponse<SettlementRecord[]>>(
      '/api/v1/settlements/me',
    )
    return res.data.data
  },
}
