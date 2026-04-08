import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { settlementApi, SettlementRecord } from '@/api/settlementApi'
import { SYMBOL_MAP } from '@/constants/symbols'
import { AgGridReact } from 'ag-grid-react'
import { AllCommunityModule, themeQuartz, ColDef, ICellRendererParams } from 'ag-grid-community'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Alert from '@mui/material/Alert'

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

const STATUS_COLOR: Record<string, 'warning' | 'success' | 'error'> = {
  PENDING: 'warning',
  SETTLED: 'success',
  FAILED: 'error',
}

const SettlementPage = () => {
  const { data: records, isLoading, isError, error } = useQuery({
    queryKey: ['settlements', 'me'],
    queryFn: settlementApi.getMySettlements,
  })

  const cols = useMemo<ColDef<SettlementRecord>[]>(() => [
    { field: 'id', headerName: 'ID', width: 60 },
    { field: 'orderId', headerName: '주문ID', width: 80 },
    { field: 'symbol', headerName: '종목코드', width: 90 },
    {
      field: 'symbol',
      headerName: '종목명',
      width: 120,
      valueFormatter: (p) => SYMBOL_MAP[p.value]?.name ?? p.value,
    },
    {
      field: 'side',
      headerName: '구분',
      width: 75,
      cellRenderer: (p: ICellRendererParams<SettlementRecord>) => {
        if (!p.value) return '—'
        const buy = p.value === 'BUY'
        return <Chip label={buy ? '매수' : '매도'} size="small" color={buy ? 'success' : 'error'} sx={{ fontSize: 11 }} />
      },
    },
    {
      field: 'executionPrice',
      headerName: '체결가',
      width: 110,
      type: 'numericColumn',
      valueFormatter: (p) => `₩${Number(p.value).toLocaleString()}`,
    },
    {
      field: 'executionQuantity',
      headerName: '수량',
      width: 75,
      type: 'numericColumn',
      valueFormatter: (p) => Number(p.value).toLocaleString(),
    },
    {
      field: 'grossAmount',
      headerName: '총액',
      width: 120,
      type: 'numericColumn',
      valueFormatter: (p) => `₩${Number(p.value).toLocaleString()}`,
    },
    {
      field: 'commission',
      headerName: '수수료',
      width: 95,
      type: 'numericColumn',
      cellStyle: { color: '#f5a623' },
      valueFormatter: (p) => `₩${Number(p.value).toLocaleString()}`,
    },
    {
      field: 'tax',
      headerName: '세금',
      width: 85,
      type: 'numericColumn',
      cellStyle: { color: '#f5a623' },
      valueFormatter: (p) => `₩${Number(p.value).toLocaleString()}`,
    },
    {
      field: 'netAmount',
      headerName: '실수령/실지불',
      width: 130,
      type: 'numericColumn',
      cellRenderer: (p: ICellRendererParams<SettlementRecord>) => {
        if (!p.data) return '—'
        const buy = p.data.side === 'BUY'
        const color = buy ? '#ef5350' : '#26a69a'
        return `<span style="color:${color};font-weight:700">${buy ? '-' : '+'}₩${Number(p.data.netAmount).toLocaleString()}</span>`
      },
    },
    { field: 'settlementDate', headerName: '정산일', width: 110 },
    {
      field: 'status',
      headerName: '상태',
      width: 90,
      cellRenderer: (p: ICellRendererParams<SettlementRecord>) => {
        if (!p.data) return null
        const color = STATUS_COLOR[p.data.status] ?? 'default'
        return <Chip label={p.data.status} size="small" color={color} />
      },
    },
  ], [])

  if (isLoading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
  if (isError) return <Alert severity="error">{(error as Error).message}</Alert>

  return (
    <Box>
      <Typography variant="h6" sx={{ fontWeight: 700, color: '#d1d4dc', mb: 2 }}>
        정산 내역 <Chip label={`${records?.length ?? 0}건`} size="small" sx={{ ml: 1, bgcolor: '#2a2e39', color: '#787b86' }} />
      </Typography>

      <Box sx={{ height: 'calc(100vh - 180px)', width: '100%' }}>
        <AgGridReact<SettlementRecord>
          modules={[AllCommunityModule]}
          theme={darkTheme}
          rowData={records ?? []}
          columnDefs={cols}
          defaultColDef={{ sortable: true, filter: true, resizable: true }}
          animateRows
          pagination
          paginationPageSize={20}
          suppressCellFocus
        />
      </Box>
    </Box>
  )
}

export default SettlementPage
