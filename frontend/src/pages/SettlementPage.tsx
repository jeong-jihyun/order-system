import { useQuery } from '@tanstack/react-query'
import { settlementApi, SettlementRecord } from '@/api/settlementApi'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorFallback from '@/components/common/ErrorFallback'

const STATUS_COLOR: Record<string, string> = {
  PENDING: '#f5a623',
  SETTLED: '#34a853',
  FAILED: '#d93025',
}

const SettlementPage = () => {
  const { data: records, isLoading, isError, error } = useQuery({
    queryKey: ['settlements', 'me'],
    queryFn: settlementApi.getMySettlements,
  })

  if (isLoading) return <LoadingSpinner message="정산 내역 불러오는 중..." />
  if (isError) return <ErrorFallback error={error as Error} />

  return (
    <div>
      <h2 style={styles.pageTitle}>정산 내역 ({records?.length ?? 0}건)</h2>

      {records?.length === 0 && (
        <div style={styles.empty}>정산 내역이 없습니다.</div>
      )}

      <div style={styles.tableWrap}>
        <table style={styles.table}>
          <thead>
            <tr style={styles.thead}>
              <th>ID</th>
              <th>주문 ID</th>
              <th>종목</th>
              <th>구분</th>
              <th>체결가</th>
              <th>체결 수량</th>
              <th>총액</th>
              <th>수수료</th>
              <th>세금</th>
              <th>실수령/실지불</th>
              <th>정산 예정일</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            {records?.map((r: SettlementRecord) => (
              <tr key={r.id} style={styles.tr}>
                <td style={styles.td}>{r.id}</td>
                <td style={styles.td}>{r.orderId}</td>
                <td style={{ ...styles.td, fontWeight: 700 }}>{r.symbol}</td>
                <td style={{ ...styles.td, color: r.side === 'BUY' ? '#34a853' : '#d93025', fontWeight: 600 }}>
                  {r.side === 'BUY' ? '매수' : '매도'}
                </td>
                <td style={styles.td}>₩{Number(r.executionPrice).toLocaleString()}</td>
                <td style={styles.td}>{Number(r.executionQuantity).toLocaleString()}</td>
                <td style={styles.td}>₩{Number(r.grossAmount).toLocaleString()}</td>
                <td style={{ ...styles.td, color: '#f5a623' }}>₩{Number(r.commission).toLocaleString()}</td>
                <td style={{ ...styles.td, color: '#f5a623' }}>₩{Number(r.tax).toLocaleString()}</td>
                <td style={{ ...styles.td, fontWeight: 700, color: r.side === 'BUY' ? '#d93025' : '#34a853' }}>
                  {r.side === 'BUY' ? '-' : '+'}₩{Number(r.netAmount).toLocaleString()}
                </td>
                <td style={styles.td}>{r.settlementDate}</td>
                <td style={styles.td}>
                  <span style={{
                    ...styles.badge,
                    background: STATUS_COLOR[r.status] ?? '#999',
                  }}>
                    {r.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  pageTitle: { fontSize: 20, fontWeight: 700, marginBottom: 20 },
  empty: { color: '#888', padding: 40, textAlign: 'center' },
  tableWrap: { overflowX: 'auto', background: '#fff', borderRadius: 10, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  thead: { background: '#f5f5f5', fontWeight: 700 },
  tr: { borderBottom: '1px solid #f0f0f0' },
  td: { padding: '10px 12px', textAlign: 'right', whiteSpace: 'nowrap' },
  badge: { color: '#fff', padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600 },
}

export default SettlementPage
