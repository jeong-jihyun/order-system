import { useMemo, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { orderApi } from '@/api/orderApi'
import { Order, OrderStatus, ORDER_STATUS_LABEL } from '@/types/order'
import { SYMBOL_MAP } from '@/constants/symbols'
import { AgGridReact } from 'ag-grid-react'
import { AllCommunityModule, themeQuartz, ColDef, ICellRendererParams } from 'ag-grid-community'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Alert from '@mui/material/Alert'
import AddIcon from '@mui/icons-material/Add'

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
  cellHorizontalPaddingScale: 0.8,
  rowVerticalPaddingScale: 0.9,
} as any)

const STATUS_COLOR: Record<string, 'warning' | 'info' | 'success' | 'error'> = {
  PENDING: 'warning',
  PROCESSING: 'info',
  COMPLETED: 'success',
  CANCELLED: 'error',
}

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
      queryClient.invalidateQueries({ queryKey: ['orders'] })
    },
  })

  const columnDefs = useMemo<ColDef<Order>[]>(() => [
    { field: 'id', headerName: 'ID', width: 70, pinned: 'left' },
    {
      field: 'side',
      headerName: '구분',
      width: 80,
      cellRenderer: (p: ICellRendererParams<Order>) => {
        if (!p.value) return '—'
        const isBuy = p.value === 'BUY'
        return `<span style="color:${isBuy ? '#26a69a' : '#ef5350'};font-weight:700">${isBuy ? '매수' : '매도'}</span>`
      },
    },
    {
      field: 'productName',
      headerName: '종목코드',
      width: 100,
    },
    {
      field: 'productName',
      headerName: '종목명',
      width: 130,
      valueFormatter: (p) => SYMBOL_MAP[p.value]?.name ?? p.value,
    },
    { field: 'customerName', headerName: '고객', width: 100 },
    {
      field: 'quantity',
      headerName: '수량',
      width: 80,
      type: 'numericColumn',
      valueFormatter: (p) => p.value?.toLocaleString() + '주',
    },
    {
      field: 'totalPrice',
      headerName: '주문가',
      width: 120,
      type: 'numericColumn',
      valueFormatter: (p) => p.value != null ? `₩${Number(p.value).toLocaleString()}` : '—',
    },
    {
      field: 'status',
      headerName: '상태',
      width: 100,
      cellRenderer: (p: ICellRendererParams<Order>) => {
        if (!p.data) return null
        const color = STATUS_COLOR[p.data.status] ?? 'default'
        const label = ORDER_STATUS_LABEL[p.data.status] ?? p.data.status
        return <Chip label={label} color={color} size="small" />
      },
    },
    {
      field: 'createdAt',
      headerName: '주문시간',
      flex: 1,
      minWidth: 160,
      valueFormatter: (p) => p.value ? new Date(p.value).toLocaleString('ko-KR') : '—',
    },
    {
      headerName: '액션',
      width: 120,
      sortable: false,
      filter: false,
      cellRenderer: (p: ICellRendererParams<Order>) => {
        if (!p.data) return null
        const o = p.data
        if (o.status === 'PENDING') {
          return (
            <Button
              size="small"
              color="error"
              variant="text"
              sx={{ fontSize: 11, minWidth: 0 }}
              disabled={updateStatusMutation.isPending}
              onClick={() => updateStatusMutation.mutate({ id: o.id, status: 'CANCELLED' })}
            >
              취소
            </Button>
          )
        }
        return null
      },
    },
  ], [updateStatusMutation])

  const defaultColDef = useMemo<ColDef>(() => ({
    sortable: true,
    filter: true,
    resizable: true,
  }), [])

  const getRowId = useCallback((params: { data: Order }) => String(params.data.id), [])

  if (isLoading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
  if (isError) return <Alert severity="error">{(error as Error).message}</Alert>

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, color: '#d1d4dc' }}>
          주문 목록 <Chip label={`${orders?.length ?? 0}건`} size="small" sx={{ ml: 1, bgcolor: '#2a2e39', color: '#787b86' }} />
        </Typography>
        <Button
          component={Link}
          to="/orders/new"
          variant="contained"
          startIcon={<AddIcon />}
          size="small"
        >
          새 주문
        </Button>
      </Box>

      <Box sx={{ height: 'calc(100vh - 180px)', width: '100%' }}>
        <AgGridReact<Order>
          modules={[AllCommunityModule]}
          theme={darkTheme}
          rowData={orders ?? []}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          getRowId={getRowId}
          animateRows
          pagination
          paginationPageSize={20}
          rowSelection="single"
          suppressCellFocus
        />
      </Box>
    </Box>
  )
}

export default OrderListPage
