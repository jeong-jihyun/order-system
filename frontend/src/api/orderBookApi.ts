import { apiClient } from './axiosConfig'

export interface PriceLevel {
  price: number
  quantity: number
  orderCount: number
}

export interface OrderBookSnapshot {
  symbol: string
  bids: PriceLevel[]
  asks: PriceLevel[]
}

interface ApiResponse<T> {
  success: boolean
  message: string
  data: T
}

export const orderBookApi = {
  getSnapshot: async (symbol: string, depth = 10): Promise<OrderBookSnapshot> => {
    const res = await apiClient.get<ApiResponse<OrderBookSnapshot>>(
      `/api/v1/orderbook/${symbol}`,
      { params: { depth } },
    )
    return res.data.data
  },
}
