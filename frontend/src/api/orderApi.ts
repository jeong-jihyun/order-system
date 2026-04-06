import { apiClient } from './axiosConfig'
import { ApiResponse, Order, OrderRequest, OrderStatus } from '@/types/order'

const BASE = '/api/orders'

export const orderApi = {
  /** 전체 주문 조회 */
  getAll: async (): Promise<Order[]> => {
    const res = await apiClient.get<ApiResponse<Order[]>>(BASE)
    return res.data.data
  },

  /** 단건 주문 조회 */
  getById: async (id: number): Promise<Order> => {
    const res = await apiClient.get<ApiResponse<Order>>(`${BASE}/${id}`)
    return res.data.data
  },

  /** 상태별 주문 조회 */
  getByStatus: async (status: OrderStatus): Promise<Order[]> => {
    const res = await apiClient.get<ApiResponse<Order[]>>(`${BASE}/status/${status}`)
    return res.data.data
  },

  /** 주문 생성 */
  create: async (data: OrderRequest): Promise<Order> => {
    const res = await apiClient.post<ApiResponse<Order>>(BASE, data)
    return res.data.data
  },

  /** 주문 상태 변경 */
  updateStatus: async (id: number, status: OrderStatus): Promise<Order> => {
    const res = await apiClient.patch<ApiResponse<Order>>(
      `${BASE}/${id}/status?status=${status}`,
    )
    return res.data.data
  },
}
