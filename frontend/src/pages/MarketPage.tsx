import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { marketApi, TickerDto, OhlcvDto } from '@/api/marketApi'
import LoadingSpinner from '@/components/common/LoadingSpinner'

const SYMBOLS = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL']

const MarketPage = () => {
  const [symbol, setSymbol] = useState('AAPL')
  const [interval, setInterval] = useState('1m')
  const [liveTicker, setLiveTicker] = useState<TickerDto | null>(null)
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')
  const wsRef = useRef<WebSocket | null>(null)

  // REST 시세 조회 (최초 로드 + fallback)
  const { data: ticker, isLoading: tickerLoading } = useQuery({
    queryKey: ['ticker', symbol],
    queryFn: () => marketApi.getTicker(symbol),
    refetchInterval: 5000,
  })

  // OHLCV 데이터
  const { data: ohlcvList, isLoading: ohlcvLoading } = useQuery({
    queryKey: ['ohlcv', symbol, interval],
    queryFn: () => marketApi.getOhlcv(symbol, interval, 20),
  })

  // STOMP WebSocket 실시간 구독 (SockJS + STOMP 없이 WebSocket raw)
  useEffect(() => {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/websocket`
    let ws: WebSocket
    try {
      ws = new WebSocket(wsUrl)
      wsRef.current = ws
      setWsStatus('connecting')

      ws.onopen = () => {
        setWsStatus('connected')
        // STOMP CONNECT frame
        ws.send('CONNECT\naccept-version:1.2\nheart-beat:0,0\n\n\0')
      }

      ws.onmessage = (evt) => {
        const frame = evt.data as string
        if (frame.startsWith('CONNECTED')) {
          // STOMP SUBSCRIBE
          ws.send(`SUBSCRIBE\nid:sub-0\ndestination:/topic/ticker/${symbol}\n\n\0`)
          // 구독 요청 전송
          ws.send(`SEND\ndestination:/app/subscribe/${symbol}\ncontent-length:0\n\n\0`)
        } else if (frame.startsWith('MESSAGE')) {
          const bodyStart = frame.indexOf('\n\n') + 2
          const body = frame.slice(bodyStart).replace('\0', '')
          try {
            const data = JSON.parse(body) as TickerDto
            setLiveTicker(data)
          } catch {
            // ignore parse errors
          }
        }
      }

      ws.onerror = () => setWsStatus('disconnected')
      ws.onclose = () => setWsStatus('disconnected')
    } catch {
      setWsStatus('disconnected')
    }

    return () => {
      wsRef.current?.close()
    }
  }, [symbol])

  const displayTicker = liveTicker ?? ticker

  return (
    <div>
      {/* 종목 선택 */}
      <div style={styles.toolbar}>
        <div style={styles.symbolGroup}>
          {SYMBOLS.map((s) => (
            <button
              key={s}
              style={{ ...styles.symbolBtn, ...(symbol === s ? styles.symbolBtnActive : {}) }}
              onClick={() => { setSymbol(s); setLiveTicker(null) }}
            >
              {s}
            </button>
          ))}
        </div>
        <span style={{ ...styles.wsBadge, background: wsStatus === 'connected' ? '#34a853' : wsStatus === 'connecting' ? '#f5a623' : '#999' }}>
          {wsStatus === 'connected' ? '● 실시간' : wsStatus === 'connecting' ? '○ 연결 중' : '○ 오프라인'}
        </span>
      </div>

      {/* 시세 카드 */}
      {tickerLoading ? (
        <LoadingSpinner message="시세 불러오는 중..." />
      ) : displayTicker ? (
        <div style={styles.tickerCard}>
          <div style={styles.tickerLeft}>
            <div style={styles.tickerSymbol}>{displayTicker.symbol}</div>
            <div style={styles.tickerPrice}>
              ₩{Number(displayTicker.price).toLocaleString()}
            </div>
            <div style={{
              ...styles.tickerChange,
              color: displayTicker.changeRate >= 0 ? '#34a853' : '#d93025',
            }}>
              {displayTicker.changeRate >= 0 ? '▲' : '▼'}{' '}
              {Math.abs(Number(displayTicker.change)).toLocaleString()}{' '}
              ({Math.abs(Number(displayTicker.changeRate)).toFixed(2)}%)
            </div>
          </div>
          <div style={styles.tickerRight}>
            <TickerItem label="시가" value={displayTicker.open} />
            <TickerItem label="고가" value={displayTicker.high} color="#d93025" />
            <TickerItem label="저가" value={displayTicker.low} color="#1a73e8" />
            <TickerItem label="전일 종가" value={displayTicker.prevClose} />
            <TickerItem label="거래량" value={displayTicker.volume} noFormat />
          </div>
        </div>
      ) : (
        <div style={styles.noData}>시세 데이터가 없습니다.</div>
      )}

      {/* OHLCV 테이블 */}
      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <h3 style={styles.sectionTitle}>캔들 데이터 (OHLCV)</h3>
          <div style={styles.intervalGroup}>
            {['1m', '5m', '15m', '1h', '1d'].map((iv) => (
              <button
                key={iv}
                style={{ ...styles.intervalBtn, ...(interval === iv ? styles.intervalBtnActive : {}) }}
                onClick={() => setInterval(iv)}
              >
                {iv}
              </button>
            ))}
          </div>
        </div>

        {ohlcvLoading ? (
          <LoadingSpinner message="캔들 데이터 불러오는 중..." />
        ) : (
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr style={styles.tableHeader}>
                  <th>시간</th><th>시가</th><th>고가</th><th>저가</th><th>종가</th><th>거래량</th>
                </tr>
              </thead>
              <tbody>
                {ohlcvList?.length === 0 && (
                  <tr><td colSpan={6} style={styles.noDataCell}>데이터 없음</td></tr>
                )}
                {ohlcvList?.map((row: OhlcvDto, idx: number) => {
                  const isUp = row.close >= row.open
                  return (
                    <tr key={idx} style={{ background: idx % 2 === 0 ? '#fff' : '#f9f9f9' }}>
                      <td style={styles.td}>{new Date(row.openTime).toLocaleString()}</td>
                      <td style={styles.td}>{Number(row.open).toLocaleString()}</td>
                      <td style={{ ...styles.td, color: '#d93025' }}>{Number(row.high).toLocaleString()}</td>
                      <td style={{ ...styles.td, color: '#1a73e8' }}>{Number(row.low).toLocaleString()}</td>
                      <td style={{ ...styles.td, color: isUp ? '#34a853' : '#d93025', fontWeight: 600 }}>
                        {isUp ? '▲' : '▼'} {Number(row.close).toLocaleString()}
                      </td>
                      <td style={styles.td}>{Number(row.volume).toLocaleString()}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

const TickerItem = ({ label, value, color = '#222', noFormat = false }: {
  label: string; value: number; color?: string; noFormat?: boolean
}) => (
  <div style={{ textAlign: 'right', marginBottom: 4 }}>
    <span style={{ fontSize: 12, color: '#888', marginRight: 8 }}>{label}</span>
    <span style={{ fontSize: 14, fontWeight: 600, color }}>
      {noFormat ? Number(value).toLocaleString() : `₩${Number(value).toLocaleString()}`}
    </span>
  </div>
)

const styles: Record<string, React.CSSProperties> = {
  toolbar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 },
  symbolGroup: { display: 'flex', gap: 8 },
  symbolBtn: { padding: '6px 14px', border: '1px solid #ddd', borderRadius: 6, background: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: 13 },
  symbolBtnActive: { background: '#1a73e8', color: '#fff', border: '1px solid #1a73e8' },
  wsBadge: { fontSize: 12, color: '#fff', padding: '4px 10px', borderRadius: 10, fontWeight: 600 },
  tickerCard: {
    background: '#fff', border: '1px solid #e8eaed', borderRadius: 12,
    padding: 24, marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
    boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
  },
  tickerLeft: {},
  tickerSymbol: { fontSize: 18, fontWeight: 700, color: '#555', marginBottom: 4 },
  tickerPrice: { fontSize: 36, fontWeight: 800, marginBottom: 4 },
  tickerChange: { fontSize: 16, fontWeight: 600 },
  tickerRight: { textAlign: 'right' },
  noData: { color: '#888', padding: 40, textAlign: 'center' },
  section: { background: '#fff', border: '1px solid #e8eaed', borderRadius: 10, padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' },
  sectionHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  sectionTitle: { fontSize: 16, fontWeight: 700 },
  intervalGroup: { display: 'flex', gap: 4 },
  intervalBtn: { padding: '4px 10px', border: '1px solid #ddd', borderRadius: 4, background: '#f5f5f5', cursor: 'pointer', fontSize: 12 },
  intervalBtnActive: { background: '#1a73e8', color: '#fff', border: '1px solid #1a73e8' },
  tableWrap: { overflowX: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  tableHeader: { background: '#f5f5f5' },
  td: { padding: '8px 12px', borderBottom: '1px solid #f0f0f0', textAlign: 'right' },
  noDataCell: { padding: 24, textAlign: 'center', color: '#888' },
}

export default MarketPage
