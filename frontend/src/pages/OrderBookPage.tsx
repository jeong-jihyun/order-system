import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { orderBookApi, PriceLevel } from '@/api/orderBookApi'
import { SYMBOLS, SYMBOL_MAP } from '@/constants/symbols'
import Box from '@mui/material/Box'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import ToggleButton from '@mui/material/ToggleButton'
import CircularProgress from '@mui/material/CircularProgress'
import Alert from '@mui/material/Alert'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import IconButton from '@mui/material/IconButton'
import RefreshIcon from '@mui/icons-material/Refresh'


const DEPTHS = [5, 10, 20]

const fmt = (v: number | null | undefined) => {
  if (v == null) return '—'
  const n = Number(v)
  return isNaN(n) ? '—' : n.toLocaleString('ko-KR')
}

const OrderBookPage = () => {
  const [symbol, setSymbol] = useState('AAPL')
  const [depth, setDepth] = useState(10)

  const { data: snapshot, isLoading, isError, refetch } = useQuery({
    queryKey: ['orderbook', symbol, depth],
    queryFn: () => orderBookApi.getSnapshot(symbol, depth),
    refetchInterval: 3000,
  })

  const maxQty = Math.max(
    ...(snapshot?.asks ?? []).map((l) => Number(l.quantity) || 0),
    ...(snapshot?.bids ?? []).map((l) => Number(l.quantity) || 0),
    1,
  )

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <ToggleButtonGroup exclusive size="small" value={symbol} onChange={(_, v) => v && setSymbol(v)}>
          {SYMBOLS.map((s) => (
            <ToggleButton key={s} value={s} sx={{ px: 1.5 }}>{s}</ToggleButton>
          ))}
        </ToggleButtonGroup>

        <Typography variant="body2" sx={{ color: '#787b86', ml: 'auto' }}>
          {SYMBOL_MAP[symbol]?.name} 호가창
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Typography variant="caption" sx={{ color: '#787b86' }}>depth:</Typography>
          <ToggleButtonGroup exclusive size="small" value={depth} onChange={(_, v) => v && setDepth(v)}>
            {DEPTHS.map((d) => (
              <ToggleButton key={d} value={d} sx={{ px: 1 }}>{d}</ToggleButton>
            ))}
          </ToggleButtonGroup>
          <IconButton size="small" onClick={() => refetch()} sx={{ color: '#787b86' }}><RefreshIcon fontSize="small" /></IconButton>
        </Box>
      </Box>

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
      ) : isError ? (
        <Alert severity="error">호가 데이터를 불러올 수 없습니다.</Alert>
      ) : !snapshot ? (
        <Paper sx={{ p: 4, textAlign: 'center', color: '#787b86' }}>데이터 없음</Paper>
      ) : (
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 2, alignItems: 'start' }}>
          {/* 매도 */}
          <HalfBook title="매도 (Ask)" levels={[...snapshot.asks].reverse()} color="#ef5350" maxQty={maxQty} />

          {/* 스프레드 */}
          {snapshot.asks.length > 0 && snapshot.bids.length > 0 && (
            <Paper sx={{ p: 2, textAlign: 'center', alignSelf: 'center', bgcolor: '#1e222d' }}>
              <Typography variant="caption" sx={{ color: '#787b86' }}>스프레드</Typography>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#f5a623' }}>
                ₩{fmt(Number(snapshot.asks[0].price) - Number(snapshot.bids[0].price))}
              </Typography>
            </Paper>
          )}

          {/* 매수 */}
          <HalfBook title="매수 (Bid)" levels={snapshot.bids} color="#26a69a" maxQty={maxQty} />
        </Box>
      )}
    </Box>
  )
}

const HalfBook = ({ title, levels, color, maxQty }: { title: string; levels: PriceLevel[]; color: string; maxQty: number }) => (
  <TableContainer component={Paper} sx={{ bgcolor: '#1e222d' }}>
    <Typography sx={{ p: 1.5, fontWeight: 700, fontSize: 14, color, borderBottom: '1px solid #2a2e39' }}>{title}</Typography>
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>가격</TableCell>
          <TableCell align="right">수량</TableCell>
          <TableCell align="right">건수</TableCell>
          <TableCell sx={{ width: 80 }} />
        </TableRow>
      </TableHead>
      <TableBody>
        {levels.map((lv, i) => {
          const pct = Math.min(100, (Number(lv.quantity) / maxQty) * 100)
          return (
            <TableRow key={i} sx={{ '&:hover': { bgcolor: '#262b3a' } }}>
              <TableCell sx={{ color, fontWeight: 700 }}>₩{fmt(lv.price)}</TableCell>
              <TableCell align="right">{fmt(lv.quantity)}</TableCell>
              <TableCell align="right">{lv.orderCount ?? '—'}</TableCell>
              <TableCell sx={{ p: 0 }}>
                <Box sx={{ height: 14, width: `${pct}%`, bgcolor: color, opacity: 0.25, borderRadius: 0.5, ml: 'auto' }} />
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  </TableContainer>
)

export default OrderBookPage
