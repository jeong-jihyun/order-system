import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { orderApi } from '@/api/orderApi'
import { Order, OrderStatus } from '@/types/order'
import OrderCard from '@/components/OrderCard'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorFallback from '@/components/common/ErrorFallback'

/**
 * [Week 3 실습 포인트]
 * - useQuery: 서버 상태 관리 (로딩/에러/성공 상태 자동 처리)
 * - useMutation: 상태 변경 후 캐시 무효화(invalidateQueries)
 * - 로딩 / 에러 분기 처리
 */
const OrderListPage = () => {
  const queryClient = useQueryClient()

  const { data: orders, isLoading, isError, error } = useQuery({
    queryKey: ['orders'],
    queryFn: orderApi.getAll,
  })

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: OrderStatus }) =>
      orderApi.updateStatus(id, status),
    onSuccess: () => {
      // 주문 목록 캐시 무효화 → 자동 재조회
      queryClient.invalidateQueries({ queryKey: ['orders'] })
    },
  })

  if (isLoading) return <LoadingSpinner message="주문 목록 불러오는 중..." />
  if (isError) return <ErrorFallback error={error as Error} />

  return (
    <div>
      <div style={styles.toolbar}>
        <h2 style={styles.title}>주문 목록 ({orders?.length ?? 0}건)</h2>
        <Link to="/orders/new">
          <button style={styles.createBtn}>+ 새 주문 등록</button>
        </Link>
      </div>

      {orders?.length === 0 ? (
        <div style={styles.empty}>등록된 주문이 없습니다.</div>
      ) : (
        <div style={styles.grid}>
          {orders?.map((order: Order) => (
            <OrderCard
              key={order.id}
              order={order}
              isUpdating={updateStatusMutation.isPending}
              onUpdateStatus={(status) =>
                updateStatusMutation.mutate({ id: order.id, status })
              }
            />
          ))}
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  toolbar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  title: { fontSize: 20, fontWeight: 700 },
  createBtn: {
    padding: '8px 18px',
    background: '#1a73e8',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    fontWeight: 600,
    fontSize: 14,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: 16,
  },
  empty: {
    textAlign: 'center',
    padding: 48,
    color: '#888',
    background: '#fff',
    borderRadius: 8,
  },
}

export default OrderListPage
