import { Order, OrderStatus, ORDER_STATUS_LABEL, ORDER_STATUS_COLOR } from '@/types/order'

interface OrderCardProps {
  order: Order
  onUpdateStatus: (status: OrderStatus) => void
  isUpdating?: boolean
}

const NEXT_STATUS: Partial<Record<OrderStatus, OrderStatus>> = {
  PENDING: 'PROCESSING',
  PROCESSING: 'COMPLETED',
}

/**
 * [Week 3 - 컴포넌트 실습]
 * 주문 카드 — props 타입 명확히 정의, 조건부 렌더링 연습
 */
const OrderCard = ({ order, onUpdateStatus, isUpdating = false }: OrderCardProps) => {
  const nextStatus = NEXT_STATUS[order.status]

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <span style={styles.id}>#{order.id}</span>
        <span
          style={{
            ...styles.badge,
            background: ORDER_STATUS_COLOR[order.status],
          }}
        >
          {ORDER_STATUS_LABEL[order.status]}
        </span>
      </div>

      <div style={styles.body}>
        <Row label="고객" value={order.customerName} />
        <Row label="상품" value={order.productName} />
        <Row label="수량" value={`${order.quantity}개`} />
        <Row label="금액" value={`₩${order.totalPrice.toLocaleString()}`} />
        <Row label="주문일" value={new Date(order.createdAt).toLocaleString()} />
      </div>

      {nextStatus && (
        <div style={styles.footer}>
          <button
            style={{ ...styles.button, opacity: isUpdating ? 0.6 : 1 }}
            onClick={() => onUpdateStatus(nextStatus)}
            disabled={isUpdating}
          >
            {isUpdating ? '처리 중...' : `→ ${ORDER_STATUS_LABEL[nextStatus]} 처리`}
          </button>
        </div>
      )}

      {order.status === 'PENDING' && (
        <div style={styles.footer}>
          <button
            style={{ ...styles.button, background: '#d93025', marginTop: 4 }}
            onClick={() => onUpdateStatus('CANCELLED')}
            disabled={isUpdating}
          >
            주문 취소
          </button>
        </div>
      )}
    </div>
  )
}

const Row = ({ label, value }: { label: string; value: string }) => (
  <div style={{ display: 'flex', gap: 8, padding: '4px 0' }}>
    <span style={{ color: '#888', minWidth: 48, fontSize: 13 }}>{label}</span>
    <span style={{ fontSize: 14, fontWeight: 500 }}>{value}</span>
  </div>
)

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: '#fff',
    borderRadius: 8,
    padding: 20,
    boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
    border: '1px solid #e0e0e0',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  id: { fontWeight: 700, fontSize: 16, color: '#333' },
  badge: {
    padding: '3px 10px',
    borderRadius: 12,
    color: '#fff',
    fontSize: 12,
    fontWeight: 600,
  },
  body: { display: 'flex', flexDirection: 'column', gap: 2 },
  footer: { marginTop: 12 },
  button: {
    width: '100%',
    padding: '8px 0',
    background: '#1a73e8',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    fontSize: 14,
    fontWeight: 600,
  },
}

export default OrderCard
