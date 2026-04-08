import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { orderBookApi, PriceLevel } from '@/api/orderBookApi'
import LoadingSpinner from '@/components/common/LoadingSpinner'

const SYMBOLS = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL']
const DEPTHS = [5, 10, 20]

const OrderBookPage = () => {
  const [symbol, setSymbol] = useState('AAPL')
  const [depth, setDepth] = useState(10)

  const { data: snapshot, isLoading, isError, refetch } = useQuery({
    queryKey: ['orderbook', symbol, depth],
    queryFn: () => orderBookApi.getSnapshot(symbol, depth),
    refetchInterval: 3000,
  })

  return (
    <div>
      <div style={styles.toolbar}>
        <div style={styles.symbolGroup}>
          {SYMBOLS.map((s) => (
            <button
              key={s}
              style={{ ...styles.symbolBtn, ...(symbol === s ? styles.symbolBtnActive : {}) }}
              onClick={() => setSymbol(s)}
            >
              {s}
            </button>
          ))}
        </div>
        <div style={styles.depthGroup}>
          <span style={{ fontSize: 13, color: '#666', marginRight: 8 }}>호가 depth:</span>
          {DEPTHS.map((d) => (
            <button
              key={d}
              style={{ ...styles.depthBtn, ...(depth === d ? styles.depthBtnActive : {}) }}
              onClick={() => setDepth(d)}
            >
              {d}
            </button>
          ))}
          <button style={styles.refreshBtn} onClick={() => refetch()}>↻ 새로고침</button>
        </div>
      </div>

      {isLoading ? (
        <LoadingSpinner message="호가창 불러오는 중..." />
      ) : isError ? (
        <div style={styles.errorBox}>호가 데이터를 불러올 수 없습니다. (trading-engine 서비스 상태 확인 필요)</div>
      ) : !snapshot ? (
        <div style={styles.empty}>데이터 없음</div>
      ) : (
        <div style={styles.bookWrap}>
          {/* 매도(asks) — 낮은 가격 우선으로 역순 표시 */}
          <div style={styles.half}>
            <h3 style={{ ...styles.side, color: '#1a73e8' }}>매도 (Ask)</h3>
            <table style={styles.table}>
              <thead>
                <tr style={styles.thead}>
                  <th style={styles.th}>가격</th>
                  <th style={styles.th}>수량</th>
                  <th style={styles.th}>건수</th>
                </tr>
              </thead>
              <tbody>
                {[...snapshot.asks].reverse().map((level: PriceLevel, idx: number) => (
                  <tr key={idx} style={{ background: idx % 2 === 0 ? '#f0f6ff' : '#fff' }}>
                    <td style={{ ...styles.td, color: '#1a73e8', fontWeight: 700 }}>
                      ₩{Number(level.price).toLocaleString()}
                    </td>
                    <td style={styles.td}>{Number(level.quantity).toLocaleString()}</td>
                    <td style={styles.td}>{level.orderCount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 스프레드 표시 */}
          {snapshot.asks.length > 0 && snapshot.bids.length > 0 && (
            <div style={styles.spread}>
              <span style={styles.spreadLabel}>스프레드</span>
              <span style={styles.spreadValue}>
                ₩{(Number(snapshot.asks[0].price) - Number(snapshot.bids[0].price)).toLocaleString()}
              </span>
            </div>
          )}

          {/* 매수(bids) — 높은 가격 우선 */}
          <div style={styles.half}>
            <h3 style={{ ...styles.side, color: '#34a853' }}>매수 (Bid)</h3>
            <table style={styles.table}>
              <thead>
                <tr style={styles.thead}>
                  <th style={styles.th}>가격</th>
                  <th style={styles.th}>수량</th>
                  <th style={styles.th}>건수</th>
                </tr>
              </thead>
              <tbody>
                {snapshot.bids.map((level: PriceLevel, idx: number) => (
                  <tr key={idx} style={{ background: idx % 2 === 0 ? '#f0fff4' : '#fff' }}>
                    <td style={{ ...styles.td, color: '#34a853', fontWeight: 700 }}>
                      ₩{Number(level.price).toLocaleString()}
                    </td>
                    <td style={styles.td}>{Number(level.quantity).toLocaleString()}</td>
                    <td style={styles.td}>{level.orderCount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  toolbar: { display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 },
  symbolGroup: { display: 'flex', gap: 8 },
  symbolBtn: { padding: '6px 14px', border: '1px solid #ddd', borderRadius: 6, background: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: 13 },
  symbolBtnActive: { background: '#1a73e8', color: '#fff', border: '1px solid #1a73e8' },
  depthGroup: { display: 'flex', alignItems: 'center', gap: 6 },
  depthBtn: { padding: '4px 10px', border: '1px solid #ddd', borderRadius: 4, background: '#f5f5f5', cursor: 'pointer', fontSize: 12 },
  depthBtnActive: { background: '#555', color: '#fff', border: '1px solid #555' },
  refreshBtn: { padding: '4px 10px', border: '1px solid #ddd', borderRadius: 4, background: '#fff', cursor: 'pointer', fontSize: 12, marginLeft: 4 },
  bookWrap: { display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 16, alignItems: 'start' },
  half: { background: '#fff', borderRadius: 10, overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.08)' },
  side: { fontSize: 15, fontWeight: 700, padding: '12px 16px', margin: 0, borderBottom: '1px solid #f0f0f0' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  thead: { background: '#f9f9f9' },
  th: { padding: '8px 12px', textAlign: 'right', fontWeight: 600, color: '#555' },
  td: { padding: '8px 12px', textAlign: 'right', borderBottom: '1px solid #f5f5f5' },
  spread: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    background: '#fff', borderRadius: 10, padding: '16px 20px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
  },
  spreadLabel: { fontSize: 11, color: '#888', marginBottom: 4 },
  spreadValue: { fontSize: 18, fontWeight: 700, color: '#f5a623' },
  errorBox: { background: '#fff3f3', color: '#c00', border: '1px solid #fcc', borderRadius: 8, padding: '16px 20px', fontSize: 14 },
  empty: { color: '#888', textAlign: 'center', padding: 40 },
}

export default OrderBookPage
