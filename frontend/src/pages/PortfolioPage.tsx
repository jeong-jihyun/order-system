import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { holdingApi, HoldingDto } from '@/api/holdingApi'
import { marketApi } from '@/api/marketApi'
import { SYMBOL_MAP } from '@/constants/symbols'
import { AgGridReact } from 'ag-grid-react'
import { AllCommunityModule, themeQuartz, ColDef } from 'ag-grid-community'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Paper from '@mui/material/Paper'
import Grid from '@mui/material/Grid'
import CircularProgress from '@mui/material/CircularProgress'
import Alert from '@mui/material/Alert'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet'

const darkTheme = themeQuartz.withParams({
  backgroundColor: '#1e222d',
  foregroundColor: '#d1d4dc',
  borderColor: '#2a2e39',
  rowHoverColor: '#262b3a',
  selectedRowBackgroundColor: '#2a2e39',
  oddRowBackgroundColor: '#1a1e29',
  chromeBackgroundColor: '#131722',
  fontFamily: '"Noto Sans KR", Roboto, sans-serif',
  fontSize: 13,
  headerFontSize: 12,
  headerFontWeight: 700,
} as any)

const fmt = (v: number) => `₩${v.toLocaleString('ko-KR')}`

interface HoldingRow extends HoldingDto {
  symbolName: string
  currentPrice: number
  evalAmount: number
  profitLoss: number
  profitRate: number
}

const PortfolioPage = () => {
  const { data: holdings, isLoading, isError } = useQuery({
    queryKey: ['holdings'],
    queryFn: holdingApi.getMyHoldings,
    refetchInterval: 10000,
  })

  // 각 보유 종목의 현재가 조회
  const symbols = useMemo(() => (holdings ?? []).map(h => h.symbol), [holdings])
  const tickerQueries = useQuery({
    queryKey: ['tickers-portfolio', symbols.join(',')],
    queryFn: async () => {
      const results: Record<string, number> = {}
      for (const sym of symbols) {
        try {
          const t = await marketApi.getTicker(sym)
          results[sym] = t?.price ?? 0
        } catch { results[sym] = 0 }
      }
      return results
    },
    enabled: symbols.length > 0,
    refetchInterval: 10000,
  })

  const rows: HoldingRow[] = useMemo(() => {
    if (!holdings) return []
    const prices = tickerQueries.data ?? {}
    return holdings.map(h => {
      const currentPrice = prices[h.symbol] ?? 0
      const evalAmount = currentPrice * h.quantity
      const profitLoss = evalAmount - h.totalInvestment
      const profitRate = h.totalInvestment > 0 ? (profitLoss / h.totalInvestment) * 100 : 0
      return {
        ...h,
        symbolName: SYMBOL_MAP[h.symbol]?.name ?? h.symbol,
        currentPrice,
        evalAmount,
        profitLoss,
        profitRate,
      }
    })
  }, [holdings, tickerQueries.data])

  const totalInvestment = rows.reduce((s, r) => s + r.totalInvestment, 0)
  const totalEval = rows.reduce((s, r) => s + r.evalAmount, 0)
  const totalPL = totalEval - totalInvestment
  const totalRate = totalInvestment > 0 ? (totalPL / totalInvestment) * 100 : 0

  const colDefs: ColDef<HoldingRow>[] = useMemo(() => [
    { field: 'symbol', headerName: '종목코드', width: 100 },
    { field: 'symbolName', headerName: '종목명', width: 130 },
    { field: 'quantity', headerName: '보유수량', width: 100, type: 'rightAligned',
      valueFormatter: p => p.value?.toLocaleString() ?? '0' },
    { field: 'averagePrice', headerName: '평균단가', width: 120, type: 'rightAligned',
      valueFormatter: p => fmt(Math.round(p.value ?? 0)) },
    { field: 'currentPrice', headerName: '현재가', width: 120, type: 'rightAligned',
      valueFormatter: p => fmt(p.value ?? 0) },
    { field: 'totalInvestment', headerName: '투자금액', width: 130, type: 'rightAligned',
      valueFormatter: p => fmt(Math.round(p.value ?? 0)) },
    { field: 'evalAmount', headerName: '평가금액', width: 130, type: 'rightAligned',
      valueFormatter: p => fmt(Math.round(p.value ?? 0)) },
    { field: 'profitLoss', headerName: '평가손익', width: 130, type: 'rightAligned',
      valueFormatter: p => fmt(Math.round(p.value ?? 0)),
      cellStyle: p => ({ color: (p.value ?? 0) >= 0 ? '#26a69a' : '#ef5350' }) },
    { field: 'profitRate', headerName: '수익률', width: 100, type: 'rightAligned',
      valueFormatter: p => `${(p.value ?? 0).toFixed(2)}%`,
      cellStyle: p => ({ color: (p.value ?? 0) >= 0 ? '#26a69a' : '#ef5350' }) },
  ], [])

  if (isLoading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress /></Box>
  if (isError) return <Alert severity="error">보유 종목을 불러오지 못했습니다.</Alert>

  return (
    <Box>
      <Typography variant="h6" sx={{ fontWeight: 700, color: '#d1d4dc', mb: 2 }}>
        <AccountBalanceWalletIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        포트폴리오
      </Typography>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid size={{ xs: 12, md: 3 }}>
          <Paper sx={{ p: 2, bgcolor: '#1e222d', border: '1px solid #2a2e39' }}>
            <Typography variant="caption" sx={{ color: '#787b86' }}>총 투자금액</Typography>
            <Typography variant="h6" sx={{ color: '#d1d4dc', fontWeight: 700 }}>{fmt(Math.round(totalInvestment))}</Typography>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Paper sx={{ p: 2, bgcolor: '#1e222d', border: '1px solid #2a2e39' }}>
            <Typography variant="caption" sx={{ color: '#787b86' }}>총 평가금액</Typography>
            <Typography variant="h6" sx={{ color: '#d1d4dc', fontWeight: 700 }}>{fmt(Math.round(totalEval))}</Typography>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Paper sx={{ p: 2, bgcolor: '#1e222d', border: '1px solid #2a2e39' }}>
            <Typography variant="caption" sx={{ color: '#787b86' }}>총 평가손익</Typography>
            <Typography variant="h6" sx={{ color: totalPL >= 0 ? '#26a69a' : '#ef5350', fontWeight: 700 }}>
              {totalPL >= 0 ? <TrendingUpIcon sx={{ fontSize: 18, mr: 0.5 }} /> : <TrendingDownIcon sx={{ fontSize: 18, mr: 0.5 }} />}
              {fmt(Math.round(totalPL))}
            </Typography>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Paper sx={{ p: 2, bgcolor: '#1e222d', border: '1px solid #2a2e39' }}>
            <Typography variant="caption" sx={{ color: '#787b86' }}>총 수익률</Typography>
            <Typography variant="h6" sx={{ color: totalRate >= 0 ? '#26a69a' : '#ef5350', fontWeight: 700 }}>
              {totalRate.toFixed(2)}%
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {rows.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center', bgcolor: '#1e222d', border: '1px solid #2a2e39' }}>
          <Typography sx={{ color: '#787b86' }}>보유 종목이 없습니다.</Typography>
        </Paper>
      ) : (
        <Box sx={{ height: 400 }}>
          <AgGridReact<HoldingRow>
            theme={darkTheme}
            modules={[AllCommunityModule]}
            rowData={rows}
            columnDefs={colDefs}
            defaultColDef={{ sortable: true, resizable: true }}
            animateRows
          />
        </Box>
      )}
    </Box>
  )
}

export default PortfolioPage
