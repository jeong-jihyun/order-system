import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { accountApi, AccountResponse, CreateAccountRequest } from '@/api/accountApi'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import Paper from '@mui/material/Paper'
import Chip from '@mui/material/Chip'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import DialogContent from '@mui/material/DialogContent'
import DialogActions from '@mui/material/DialogActions'
import TextField from '@mui/material/TextField'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import ToggleButton from '@mui/material/ToggleButton'
import Alert from '@mui/material/Alert'
import CircularProgress from '@mui/material/CircularProgress'
import Grid from '@mui/material/Grid'
import AddIcon from '@mui/icons-material/Add'

type Action = 'deposit' | 'withdraw'

const TYPE_LABEL: Record<string, string> = {
  CASH: '현금 계좌',
  STOCK: '주식 계좌',
  DERIVATIVE: '파생 계좌',
}

const AccountPage = () => {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<{ account: AccountResponse; action: Action } | null>(null)
  const [amount, setAmount] = useState('')
  const [actionError, setActionError] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [newType, setNewType] = useState<CreateAccountRequest['accountType']>('CASH')

  const { data: accounts, isLoading, isError, error } = useQuery({
    queryKey: ['accounts', 'me'],
    queryFn: accountApi.getMyAccounts,
  })

  const mutation = useMutation({
    mutationFn: ({ id, action, amt }: { id: number; action: Action; amt: number }) =>
      action === 'deposit' ? accountApi.deposit(id, amt) : accountApi.withdraw(id, amt),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts', 'me'] })
      setSelected(null)
      setAmount('')
      setActionError('')
    },
    onError: (err: Error) => setActionError(err.message),
  })

  const createMutation = useMutation({
    mutationFn: () => accountApi.create(newType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts', 'me'] })
      setShowCreate(false)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selected) return
    const amt = parseFloat(amount)
    if (!amt || amt <= 0) { setActionError('0보다 큰 금액 입력'); return }
    mutation.mutate({ id: selected.account.id, action: selected.action, amt })
  }

  if (isLoading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
  if (isError) return <Alert severity="error">{(error as Error).message}</Alert>

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2.5 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, color: '#d1d4dc' }}>내 계좌</Typography>
        <Button variant="contained" startIcon={<AddIcon />} size="small" onClick={() => { setNewType('CASH'); setShowCreate(true) }}>
          계좌 추가
        </Button>
      </Box>

      {accounts?.length === 0 && (
        <Paper sx={{ p: 5, textAlign: 'center', color: '#787b86' }}>등록된 계좌가 없습니다.</Paper>
      )}

      <Grid container spacing={2}>
        {accounts?.map((acc) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={acc.id}>
            <Paper sx={{ p: 2.5, bgcolor: '#1e222d', border: '1px solid #2a2e39' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography sx={{ fontWeight: 700 }}>{TYPE_LABEL[acc.accountType] ?? acc.accountType}</Typography>
                <Chip label={acc.active ? '활성' : '비활성'} size="small" color={acc.active ? 'success' : 'default'} />
              </Box>
              <Typography variant="caption" sx={{ color: '#787b86', letterSpacing: 1, display: 'block', mb: 2 }}>{acc.accountNumber}</Typography>

              <Row label="총 잔고" value={acc.balance} />
              <Row label="동결" value={acc.frozenBalance} color="#f5a623" />
              <Row label="출금 가능" value={acc.availableBalance} color="#2962ff" bold />

              <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                <Button fullWidth size="small" variant="outlined" color="success" onClick={() => { setSelected({ account: acc, action: 'deposit' }); setAmount(''); setActionError('') }}>입금</Button>
                <Button fullWidth size="small" variant="outlined" color="error" onClick={() => { setSelected({ account: acc, action: 'withdraw' }); setAmount(''); setActionError('') }}>출금</Button>
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* 입금/출금 다이얼로그 */}
      <Dialog open={!!selected} onClose={() => setSelected(null)} slotProps={{ paper: { sx: { bgcolor: '#1e222d', border: '1px solid #2a2e39', minWidth: 340 } } }}>
        <DialogTitle sx={{ fontWeight: 700 }}>
          {selected?.action === 'deposit' ? '입금' : '출금'} — {selected?.account.accountNumber}
        </DialogTitle>
        <form onSubmit={handleSubmit}>
          <DialogContent>
            <Typography variant="body2" sx={{ color: '#787b86', mb: 2 }}>
              출금 가능: <strong style={{ color: '#d1d4dc' }}>₩{selected?.account.availableBalance.toLocaleString()}</strong>
            </Typography>
            {actionError && <Alert severity="error" sx={{ mb: 2 }}>{actionError}</Alert>}
            <TextField fullWidth label="금액 (원)" type="number" value={amount} onChange={(e) => { setAmount(e.target.value); setActionError('') }} autoFocus />
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2 }}>
            <Button onClick={() => setSelected(null)}>취소</Button>
            <Button type="submit" variant="contained" color={selected?.action === 'deposit' ? 'success' : 'error'} disabled={mutation.isPending}>
              {mutation.isPending ? '처리 중...' : '확인'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* 계좌 추가 다이얼로그 */}
      <Dialog open={showCreate} onClose={() => setShowCreate(false)} slotProps={{ paper: { sx: { bgcolor: '#1e222d', border: '1px solid #2a2e39', minWidth: 340 } } }}>
        <DialogTitle sx={{ fontWeight: 700 }}>새 계좌 추가</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ color: '#787b86', mb: 2 }}>계좌 유형을 선택하세요</Typography>
          <ToggleButtonGroup
            exclusive
            fullWidth
            value={newType}
            onChange={(_, v) => v && setNewType(v)}
            sx={{ mb: 2 }}
          >
            <ToggleButton value="CASH">현금</ToggleButton>
            <ToggleButton value="STOCK">주식</ToggleButton>
            <ToggleButton value="DERIVATIVE">파생</ToggleButton>
          </ToggleButtonGroup>
          {createMutation.isError && <Alert severity="error">{(createMutation.error as Error).message}</Alert>}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setShowCreate(false)}>취소</Button>
          <Button variant="contained" disabled={createMutation.isPending} onClick={() => createMutation.mutate()}>
            {createMutation.isPending ? '생성 중...' : '계좌 생성'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

const Row = ({ label, value, color = '#d1d4dc', bold = false }: { label: string; value: number; color?: string; bold?: boolean }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.4 }}>
    <Typography variant="body2" sx={{ color: '#787b86', fontSize: 13 }}>{label}</Typography>
    <Typography variant="body2" sx={{ color, fontWeight: bold ? 700 : 400, fontSize: 13 }}>₩{value.toLocaleString()}</Typography>
  </Box>
)

export default AccountPage
