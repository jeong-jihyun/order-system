import { apiClient } from './axiosConfig'

export interface HoldingDto {
  id: number
  symbol: string
  quantity: number
  averagePrice: number
  totalInvestment: number
  updatedAt: string
}

export const holdingApi = {
  getMyHoldings: async (): Promise<HoldingDto[]> => {
    const { data } = await apiClient.get('/api/v1/holdings/me')
    return data.data ?? []
  },
}
