import { apiClient } from './axiosConfig'

export interface TickerDto {
  symbol: string
  price: number
  open: number
  high: number
  low: number
  prevClose: number
  change: number
  changeRate: number
  volume: number
  turnover: number
  timestamp: string
}

export interface OhlcvDto {
  symbol: string
  interval: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  openTime: string
  closeTime: string
}

interface ApiResponse<T> {
  success: boolean
  message: string
  data: T
}

const BASE = '/api/v1/market'

export const marketApi = {
  getTicker: async (symbol: string): Promise<TickerDto> => {
    const res = await apiClient.get<ApiResponse<TickerDto>>(`${BASE}/ticker/${symbol}`)
    return res.data.data
  },

  getOhlcv: async (
    symbol: string,
    interval = '1m',
    limit = 100,
  ): Promise<OhlcvDto[]> => {
    const res = await apiClient.get<ApiResponse<OhlcvDto[]>>(
      `${BASE}/ohlcv/${symbol}`,
      { params: { interval, limit } },
    )
    return res.data.data
  },
}
