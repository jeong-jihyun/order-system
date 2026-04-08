import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { marketApi, TickerDto } from '@/api/marketApi'
import { SYMBOLS, SYMBOL_MAP } from '@/constants/symbols'
import Box from '@mui/material/Box'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import ToggleButton from '@mui/material/ToggleButton'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'

const fmt = (v: number | null | undefined) => {
  if (v == null) return '—'
  const n = Number(v)
  return isNaN(n) ? '—' : `₩${n.toLocaleString('ko-KR')}`
}

const fmtPct = (v: number | null | undefined) => {
  if (v == null) return '—'
  const n = Number(v)
  return isNaN(n) ? '—' : `${Math.abs(n).toFixed(2)}%`
}

// TradingView 인터뱸 매핑
const INTERVALS: { label: string; tv: string }[] = [
  { label: '1m',  tv: '1'  },
  { label: '5m',  tv: '5'  },
  { label: '15m', tv: '15' },
  { label: '1h',  tv: '60' },
  { label: '1d',  tv: 'D'  },
  { label: '1w',  tv: 'W'  },
]

// TradingView Advanced Chart 위젯 컴포넌트
const TradingViewChart = ({ symbol, interval }: { symbol: string; interval: string }) => {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // 뷰포트에서 상단 UI 영역(네비바 64 + 종목선택 64 + 시세카드 130 + 차트헤더 50 + 여백 112)을 뺀 높이
    const chartHeight = Math.max(400, window.innerHeight - 420)

    container.innerHTML = ''
    container.style.height = `${chartHeight}px`

    const widgetDiv = document.createElement('div')
    widgetDiv.className = 'tradingview-widget-container__widget'
    widgetDiv.style.height = '100%'
    widgetDiv.style.width = '100%'
    container.appendChild(widgetDiv)

    const script = document.createElement('script')
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js'
    script.type = 'text/javascript'
    script.async = true
    script.textContent = JSON.stringify({
      autosize: false,
      width: '100%',
      height: chartHeight,
      symbol: `NASDAQ:${symbol}`,
      interval,
      timezone: 'Asia/Seoul',
      theme: 'dark',
      style: '1',
      locale: 'ko',
      withdateranges: true,
      allow_symbol_change: false,
      save_image: false,
      hide_volume: false,
      support_host: 'https://www.tradingview.com',
    })
    container.appendChild(script)

    return () => {
      container.innerHTML = ''
    }
  }, [symbol, interval])

  return (
    <Box
      ref={containerRef}
      className="tradingview-widget-container"
      style={{ width: '100%' }}
    />
  )
}

const MarketPage = () => {
  const [symbol, setSymbol] = useState('AAPL')
  const [interval, setInterval] = useState('D')
  const [liveTicker, setLiveTicker] = useState<TickerDto | null>(null)
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')
  const wsRef = useRef<WebSocket | null>(null)

  const { data: ticker, isLoading: tickerLoading } = useQuery({
    queryKey: ['ticker', symbol],
    queryFn: () => marketApi.getTicker(symbol),
    refetchInterval: 5000,
  })

  // WebSocket
  useEffect(() => {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/websocket`
    let ws: WebSocket
    try {
      ws = new WebSocket(wsUrl)
      wsRef.current = ws
      setWsStatus('connecting')

      ws.onopen = () => {
        setWsStatus('connected')
        ws.send('CONNECT\naccept-version:1.2\nheart-beat:0,0\n\n\0')
      }

      ws.onmessage = (evt) => {
        const frame = evt.data as string
        if (frame.startsWith('CONNECTED')) {
          ws.send(`SUBSCRIBE\nid:sub-0\ndestination:/topic/ticker/${symbol}\n\n\0`)
          ws.send(`SEND\ndestination:/app/subscribe/${symbol}\ncontent-length:0\n\n\0`)
        } else if (frame.startsWith('MESSAGE')) {
          const bodyStart = frame.indexOf('\n\n') + 2
          const body = frame.slice(bodyStart).replace('\0', '')
          try {
            const data = JSON.parse(body) as TickerDto
            if (data.price != null && !isNaN(Number(data.price))) {
              setLiveTicker(data)
            }
          } catch { /* ignore */ }
        }
      }

      ws.onerror = () => setWsStatus('disconnected')
      ws.onclose = () => setWsStatus('disconnected')
    } catch {
      setWsStatus('disconnected')
    }

    return () => { wsRef.current?.close() }
  }, [symbol])

  const displayTicker = liveTicker ?? ticker
  const priceNum = displayTicker?.price != null ? Number(displayTicker.price) : null
  const changeRateNum = displayTicker?.changeRate != null ? Number(displayTicker.changeRate) : null
  const isUp = changeRateNum != null && changeRateNum >= 0

  return (
    <Box>
      {/* 종목 선택 */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <ToggleButtonGroup exclusive size="small" value={symbol} onChange={(_, v) => { if (v) { setSymbol(v); setLiveTicker(null) } }}>
          {SYMBOLS.map((s) => (
            <ToggleButton key={s} value={s} sx={{ px: 1.5 }}>
              {s}
              <Typography variant="caption" sx={{ ml: 0.5, color: '#787b86', display: { xs: 'none', sm: 'inline' } }}>
                {SYMBOL_MAP[s].name}
              </Typography>
            </ToggleButton>
          ))}
        </ToggleButtonGroup>

        <Chip
          label={wsStatus === 'connected' ? '● 실시간' : wsStatus === 'connecting' ? '○ 연결 중' : '○ 오프라인'}
          size="small"
          sx={{
            ml: 'auto',
            bgcolor: wsStatus === 'connected' ? '#26a69a' : wsStatus === 'connecting' ? '#f5a623' : '#4c525e',
            color: '#fff',
            fontWeight: 600,
          }}
        />
      </Box>

      {/* 시세 카드 */}
      {tickerLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>
      ) : displayTicker ? (
        <Paper sx={{ p: 2.5, mb: 2, bgcolor: '#1e222d', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
          <Box>
            <Typography variant="caption" sx={{ color: '#787b86' }}>{displayTicker.symbol} — {SYMBOL_MAP[displayTicker.symbol]?.name}</Typography>
            <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1.5 }}>
              <Typography variant="h4" sx={{ fontWeight: 800, color: isUp ? '#26a69a' : '#ef5350' }}>
                {fmt(priceNum)}
              </Typography>
              {changeRateNum != null && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.3 }}>
                  {isUp ? <TrendingUpIcon sx={{ fontSize: 18, color: '#26a69a' }} /> : <TrendingDownIcon sx={{ fontSize: 18, color: '#ef5350' }} />}
                  <Typography sx={{ fontSize: 15, fontWeight: 600, color: isUp ? '#26a69a' : '#ef5350' }}>
                    {fmt(displayTicker.change != null ? Math.abs(Number(displayTicker.change)) : null)} ({fmtPct(changeRateNum)})
                  </Typography>
                </Box>
              )}
            </Box>
          </Box>

          <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
            <MiniStat label="시가" value={fmt(displayTicker.open)} />
            <MiniStat label="고가" value={fmt(displayTicker.high)} color="#ef5350" />
            <MiniStat label="저가" value={fmt(displayTicker.low)} color="#26a69a" />
            <MiniStat label="전일종가" value={fmt(displayTicker.prevClose)} />
            <MiniStat label="거래량" value={displayTicker.volume != null ? Number(displayTicker.volume).toLocaleString() : '—'} />
          </Box>
        </Paper>
      ) : (
        <Paper sx={{ p: 4, mb: 2, textAlign: 'center', color: '#787b86' }}>시세 데이터가 없습니다.</Paper>
      )}

      {/* TradingView 차트 */}
      <Paper sx={{ mb: 2, overflow: 'hidden', bgcolor: '#131722' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', px: 2, py: 1.2, borderBottom: '1px solid #2a2e39' }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#d1d4dc' }}>
            TradingView — {symbol} / {SYMBOL_MAP[symbol]?.name}
          </Typography>
          <ToggleButtonGroup exclusive size="small" value={interval} onChange={(_, v) => v && setInterval(v)}>
            {INTERVALS.map((iv) => (
              <ToggleButton key={iv.tv} value={iv.tv} sx={{ px: 1.2, fontSize: 11 }}>{iv.label}</ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Box>
        <TradingViewChart symbol={symbol} interval={interval} />
      </Paper>
    </Box>
  )
}

const MiniStat = ({ label, value, color = '#d1d4dc' }: { label: string; value: string; color?: string }) => (
  <Box sx={{ textAlign: 'right' }}>
    <Typography variant="caption" sx={{ color: '#787b86', display: 'block', lineHeight: 1 }}>{label}</Typography>
    <Typography variant="body2" sx={{ fontWeight: 600, color }}>{value}</Typography>
  </Box>
)

export default MarketPage
