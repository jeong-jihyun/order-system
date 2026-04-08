import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { orderApi } from '@/api/orderApi'
import { marketApi } from '@/api/marketApi'
import { OrderRequest, OrderSide } from '@/types/order'
import { SYMBOLS, SYMBOL_MAP } from '@/constants/symbols'
import { useAuth } from '@/context/AuthContext'
import Box from '@mui/material/Box'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import ButtonGroup from '@mui/material/ButtonGroup'
import TextField from '@mui/material/TextField'
import MenuItem from '@mui/material/MenuItem'
import Alert from '@mui/material/Alert'
import Divider from '@mui/material/Divider'
import IconButton from '@mui/material/IconButton'
import AddIcon from '@mui/icons-material/Add'
import RemoveIcon from '@mui/icons-material/Remove'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'

const OrderCreatePage = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()

  const [side, setSide] = useState<OrderSide>('BUY')
  const [symbol, setSymbol] = useState('AAPL')
  const [orderType, setOrderType] = useState<'LIMIT' | 'MARKET'>('LIMIT')
  const [quantity, setQuantity] = useState(1)
  const [price, setPrice] = useState(0)
  const [error, setError] = useState('')

  const { data: ticker } = useQuery({
    queryKey: ['ticker', symbol],
    queryFn: () => marketApi.getTicker(symbol),
    refetchInterval: 5000,
  })

  const currentPrice = ticker?.price ?? null
  const changeRate = ticker?.changeRate ?? null
  const isUp = changeRate != null && Number(changeRate) >= 0

  const effectivePrice = orderType === 'MARKET' ? (currentPrice ?? 0) : price
  const totalAmount = effectivePrice > 0 ? effectivePrice * quantity : 0

  const createMutation = useMutation({
    mutationFn: (req: OrderRequest) => orderApi.create(req),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      navigate('/')
    },
    onError: (e: Error) => setError(e.message),
  })

  const tick = currentPrice ? Math.max(1, Math.round(Number(currentPrice) * 0.001)) : 50

  const handleSubmit = () => {
    if (!user) return
    if (quantity < 1) { setError('수량은 1 이상이어야 합니다.'); return }
    if (orderType === 'LIMIT' && price <= 0) { setError('지정가를 입력해주세요.'); return }
    setError('')
    createMutation.mutate({
      customerName: user.username,
      productName: symbol,
      quantity,
      totalPrice: effectivePrice,
      side,
      orderType,
    } as any)
  }

  const isBuy = side === 'BUY'
  const accentColor = isBuy ? '#26a69a' : '#ef5350'

  return (
    <Box sx={{ maxWidth: 440, mx: 'auto' }}>
      <Paper sx={{ bgcolor: '#1e222d', border: '1px solid #2a2e39', overflow: 'hidden' }}>
        {/* 매수 / 매도 탭 */}
        <Box sx={{ display: 'flex' }}>
          <Button
            fullWidth
            onClick={() => setSide('BUY')}
            sx={{
              py: 1.5,
              borderRadius: 0,
              fontSize: 16,
              fontWeight: 700,
              color: side === 'BUY' ? '#26a69a' : '#787b86',
              bgcolor: side === 'BUY' ? 'rgba(38,166,154,0.1)' : 'transparent',
              borderBottom: side === 'BUY' ? '3px solid #26a69a' : '3px solid transparent',
            }}
          >
            매수
          </Button>
          <Button
            fullWidth
            onClick={() => setSide('SELL')}
            sx={{
              py: 1.5,
              borderRadius: 0,
              fontSize: 16,
              fontWeight: 700,
              color: side === 'SELL' ? '#ef5350' : '#787b86',
              bgcolor: side === 'SELL' ? 'rgba(239,83,80,0.1)' : 'transparent',
              borderBottom: side === 'SELL' ? '3px solid #ef5350' : '3px solid transparent',
            }}
          >
            매도
          </Button>
        </Box>

        <Box sx={{ p: 2.5 }}>
          {/* 종목 선택 + 현재가 */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <TextField
              select
              label="종목"
              value={symbol}
              onChange={(e) => { setSymbol(e.target.value); setPrice(0) }}
              sx={{ minWidth: 160 }}
            >
              {SYMBOLS.map((s) => (
                <MenuItem key={s} value={s}>
                  {s} — {SYMBOL_MAP[s].name}
                </MenuItem>
              ))}
            </TextField>

            <Box sx={{ ml: 'auto', textAlign: 'right' }}>
              <Typography variant="h6" sx={{ fontWeight: 800, color: currentPrice ? accentColor : '#787b86', lineHeight: 1.2 }}>
                {currentPrice != null ? `₩${Number(currentPrice).toLocaleString()}` : '—'}
              </Typography>
              {changeRate != null && (
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.3 }}>
                  {isUp ? <TrendingUpIcon sx={{ fontSize: 14, color: '#26a69a' }} /> : <TrendingDownIcon sx={{ fontSize: 14, color: '#ef5350' }} />}
                  <Typography variant="caption" sx={{ color: isUp ? '#26a69a' : '#ef5350', fontWeight: 600 }}>
                    {Math.abs(Number(changeRate)).toFixed(2)}%
                  </Typography>
                </Box>
              )}
            </Box>
          </Box>

          {/* 주문 유형 */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="caption" sx={{ color: '#787b86', mb: 0.5, display: 'block' }}>주문 유형</Typography>
            <ButtonGroup fullWidth size="small">
              <Button
                variant={orderType === 'LIMIT' ? 'contained' : 'outlined'}
                onClick={() => setOrderType('LIMIT')}
                sx={{ borderColor: '#363a45' }}
              >
                지정가
              </Button>
              <Button
                variant={orderType === 'MARKET' ? 'contained' : 'outlined'}
                onClick={() => setOrderType('MARKET')}
                sx={{ borderColor: '#363a45' }}
              >
                시장가
              </Button>
            </ButtonGroup>
          </Box>

          {/* 수량 */}
          <TextField
            fullWidth
            label="수량"
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
            slotProps={{ input: { endAdornment: <Typography sx={{ color: '#787b86', fontSize: 13 }}>주</Typography> } }}
            sx={{ mb: 2 }}
          />

          {/* 가격 */}
          {orderType === 'LIMIT' ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 2 }}>
              <IconButton size="small" sx={{ border: '1px solid #363a45' }} onClick={() => setPrice((p) => Math.max(0, p - tick))}>
                <RemoveIcon fontSize="small" />
              </IconButton>
              <TextField
                fullWidth
                label="가격"
                type="number"
                value={price}
                onChange={(e) => setPrice(Math.max(0, Number(e.target.value)))}
                slotProps={{ htmlInput: { style: { textAlign: 'center' } } }}
              />
              <IconButton size="small" sx={{ border: '1px solid #363a45' }} onClick={() => setPrice((p) => p + tick)}>
                <AddIcon fontSize="small" />
              </IconButton>
            </Box>
          ) : (
            <Box sx={{ mb: 2, p: 1.5, bgcolor: '#262b3a', borderRadius: 1, textAlign: 'center' }}>
              <Typography variant="body2" sx={{ color: '#787b86' }}>시장가 (자동)</Typography>
            </Box>
          )}

          <Divider sx={{ mb: 2 }} />

          {/* 주문 금액 */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="body2" sx={{ color: '#787b86' }}>주문 금액</Typography>
            <Typography variant="body1" sx={{ fontWeight: 700, color: '#d1d4dc' }}>
              {totalAmount > 0 ? `₩${totalAmount.toLocaleString()}` : '—'}
            </Typography>
          </Box>

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          {/* 주문 버튼 */}
          <Button
            fullWidth
            variant="contained"
            size="large"
            onClick={handleSubmit}
            disabled={createMutation.isPending}
            sx={{
              py: 1.5,
              fontWeight: 700,
              fontSize: 16,
              bgcolor: accentColor,
              '&:hover': { bgcolor: accentColor, filter: 'brightness(1.15)' },
            }}
          >
            {createMutation.isPending
              ? '처리 중...'
              : `${isBuy ? '매수' : '매도'} 주문 (${symbol})`}
          </Button>

          <Button
            fullWidth
            variant="text"
            size="small"
            onClick={() => navigate('/')}
            sx={{ mt: 1, color: '#787b86' }}
          >
            취소
          </Button>
        </Box>
      </Paper>
    </Box>
  )
}

export default OrderCreatePage
