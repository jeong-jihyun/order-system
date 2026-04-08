import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { marketApi, TickerDto, OhlcvDto } from '@/api/marketApi'
import { SYMBOLS, SYMBOL_MAP } from '@/constants/symbols'
import { createChart, IChartApi, ISeriesApi, CandlestickData, HistogramData, Time, ColorType } from 'lightweight-charts'
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

const INTERVALS = ['1m', '5m', '15m', '1h', '1d']

const MarketPage = () => {
  const [symbol, setSymbol] = useState('AAPL')
  const [interval, setInterval] = useState('1m')
  const [liveTicker, setLiveTicker] = useState<TickerDto | null>(null)
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')
  const wsRef = useRef<WebSocket | null>(null)
  const chartContainerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)

  const { data: ticker, isLoading: tickerLoading } = useQuery({
    queryKey: ['ticker', symbol],
    queryFn: () => marketApi.getTicker(symbol),
    refetchInterval: 5000,
  })

  const { data: ohlcvList } = useQuery({
    queryKey: ['ohlcv', symbol, interval],
    queryFn: () => marketApi.getOhlcv(symbol, interval, 100),
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

  // Chart 생성 & 업데이트
  useEffect(() => {
    if (!chartContainerRef.current) return

    // 기존 차트 제거
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
    }

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { type: ColorType.Solid, color: '#131722' },
        textColor: '#787b86',
        fontFamily: '"Noto Sans KR", Roboto, sans-serif',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: '#1e222d' },
        horzLines: { color: '#1e222d' },
      },
      crosshair: {
        vertLine: { color: '#363a45', width: 1, style: 2, labelBackgroundColor: '#2a2e39' },
        horzLine: { color: '#363a45', width: 1, style: 2, labelBackgroundColor: '#2a2e39' },
      },
      rightPriceScale: { borderColor: '#2a2e39' },
      timeScale: { borderColor: '#2a2e39', timeVisible: true, secondsVisible: false },
    })
    chartRef.current = chart

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderDownColor: '#ef5350',
      borderUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      wickUpColor: '#26a69a',
    })
    candleSeriesRef.current = candleSeries

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    })
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })
    volumeSeriesRef.current = volumeSeries

    // 데이터 설정
    if (ohlcvList && ohlcvList.length > 0) {
      const candles: CandlestickData<Time>[] = ohlcvList.map((d: OhlcvDto) => ({
        time: (new Date(d.openTime).getTime() / 1000) as Time,
        open: Number(d.open),
        high: Number(d.high),
        low: Number(d.low),
        close: Number(d.close),
      }))

      const volumes: HistogramData<Time>[] = ohlcvList.map((d: OhlcvDto) => ({
        time: (new Date(d.openTime).getTime() / 1000) as Time,
        value: Number(d.volume) || 0,
        color: Number(d.close) >= Number(d.open) ? 'rgba(38,166,154,0.3)' : 'rgba(239,83,80,0.3)',
      }))

      candleSeries.setData(candles)
      volumeSeries.setData(volumes)
      chart.timeScale().fitContent()
    }

    // resize
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width })
      }
    })
    observer.observe(chartContainerRef.current)

    return () => {
      observer.disconnect()
      chart.remove()
      chartRef.current = null
    }
  }, [ohlcvList, symbol, interval])

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

      {/* 차트 */}
      <Paper sx={{ p: 0, mb: 2, overflow: 'hidden', bgcolor: '#131722' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', px: 2, py: 1.2, borderBottom: '1px solid #2a2e39' }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#d1d4dc' }}>캔들 차트</Typography>
          <ToggleButtonGroup exclusive size="small" value={interval} onChange={(_, v) => v && setInterval(v)}>
            {INTERVALS.map((iv) => (
              <ToggleButton key={iv} value={iv} sx={{ px: 1, fontSize: 11 }}>{iv}</ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Box>
        <Box ref={chartContainerRef} sx={{ width: '100%', height: 400 }} />
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
