// ─────────────────────────────────────────────
// 주문 도메인 타입 정의
// ─────────────────────────────────────────────

export type OrderStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'CANCELLED'
export type OrderSide = 'BUY' | 'SELL'

export const ORDER_STATUS_LABEL: Record<OrderStatus, string> = {
  PENDING: '대기',
  PROCESSING: '처리 중',
  COMPLETED: '완료',
  CANCELLED: '취소',
}

export const ORDER_STATUS_COLOR: Record<OrderStatus, string> = {
  PENDING: '#f5a623',
  PROCESSING: '#1a73e8',
  COMPLETED: '#34a853',
  CANCELLED: '#d93025',
}

export interface Order {
  id: number
  customerName: string
  productName: string
  quantity: number
  totalPrice: number
  side?: OrderSide
  status: OrderStatus
  createdAt: string
  updatedAt: string
}

export interface OrderRequest {
  customerName: string
  productName: string
  quantity: number
  totalPrice: number
  side?: OrderSide
}

// ─────────────────────────────────────────────
// Generic API 응답 타입 — 백엔드 ApiResponse<T> 와 1:1 대응
// ─────────────────────────────────────────────
export interface ApiResponse<T> {
  success: boolean
  message: string
  data: T
}
