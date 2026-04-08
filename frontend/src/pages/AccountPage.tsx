import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { accountApi, AccountResponse } from '@/api/accountApi'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorFallback from '@/components/common/ErrorFallback'

type Action = 'deposit' | 'withdraw'

const AccountPage = () => {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<{ account: AccountResponse; action: Action } | null>(null)
  const [amount, setAmount] = useState('')
  const [actionError, setActionError] = useState('')

  const { data: accounts, isLoading, isError, error } = useQuery({
    queryKey: ['accounts', 'me'],
    queryFn: accountApi.getMyAccounts,
  })

  const mutation = useMutation({
    mutationFn: ({ id, action, amt }: { id: number; action: Action; amt: number }) =>
      action === 'deposit'
        ? accountApi.deposit(id, amt)
        : accountApi.withdraw(id, amt),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts', 'me'] })
      setSelected(null)
      setAmount('')
      setActionError('')
    },
    onError: (err: Error) => setActionError(err.message),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selected) return
    const amt = parseFloat(amount)
    if (!amt || amt <= 0) {
      setActionError('0보다 큰 금액을 입력해주세요.')
      return
    }
    mutation.mutate({ id: selected.account.id, action: selected.action, amt })
  }

  if (isLoading) return <LoadingSpinner message="계좌 정보 불러오는 중..." />
  if (isError) return <ErrorFallback error={error as Error} />

  return (
    <div>
      <h2 style={styles.pageTitle}>내 계좌</h2>

      {accounts?.length === 0 && (
        <div style={styles.empty}>등록된 계좌가 없습니다.</div>
      )}

      <div style={styles.grid}>
        {accounts?.map((acc) => (
          <div key={acc.id} style={styles.card}>
            <div style={styles.cardHeader}>
              <span style={styles.accountType}>{acc.accountType}</span>
              <span style={{ ...styles.badge, background: acc.active ? '#34a853' : '#999' }}>
                {acc.active ? '활성' : '비활성'}
              </span>
            </div>
            <div style={styles.accountNumber}>{acc.accountNumber}</div>
            <div style={styles.balanceGrid}>
              <BalanceRow label="총 잔고" value={acc.balance} />
              <BalanceRow label="동결 금액" value={acc.frozenBalance} color="#f5a623" />
              <BalanceRow label="출금 가능" value={acc.availableBalance} color="#1a73e8" bold />
            </div>
            <div style={styles.cardFooter}>
              <button
                style={{ ...styles.actionBtn, background: '#34a853' }}
                onClick={() => { setSelected({ account: acc, action: 'deposit' }); setAmount(''); setActionError('') }}
              >
                입금
              </button>
              <button
                style={{ ...styles.actionBtn, background: '#d93025' }}
                onClick={() => { setSelected({ account: acc, action: 'withdraw' }); setAmount(''); setActionError('') }}
              >
                출금
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* 입금/출금 모달 */}
      {selected && (
        <div style={styles.overlay} onClick={() => setSelected(null)}>
          <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3 style={styles.modalTitle}>
              {selected.action === 'deposit' ? '💰 입금' : '💸 출금'} — {selected.account.accountNumber}
            </h3>
            <p style={styles.modalSub}>
              출금 가능 잔액: <strong>₩{selected.account.availableBalance.toLocaleString()}</strong>
            </p>

            {actionError && <div style={styles.errorBox}>⚠️ {actionError}</div>}

            <form onSubmit={handleSubmit} style={styles.modalForm}>
              <input
                style={styles.input}
                type="number"
                min="0.01"
                step="0.01"
                value={amount}
                onChange={(e) => { setAmount(e.target.value); setActionError('') }}
                placeholder="금액 입력 (원)"
                autoFocus
              />
              <div style={styles.modalBtns}>
                <button type="button" style={styles.cancelBtn} onClick={() => setSelected(null)}>
                  취소
                </button>
                <button
                  type="submit"
                  style={{
                    ...styles.confirmBtn,
                    background: selected.action === 'deposit' ? '#34a853' : '#d93025',
                    opacity: mutation.isPending ? 0.7 : 1,
                  }}
                  disabled={mutation.isPending}
                >
                  {mutation.isPending ? '처리 중...' : selected.action === 'deposit' ? '입금 확인' : '출금 확인'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

const BalanceRow = ({ label, value, color = '#222', bold = false }: {
  label: string; value: number; color?: string; bold?: boolean
}) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
    <span style={{ color: '#666', fontSize: 13 }}>{label}</span>
    <span style={{ color, fontWeight: bold ? 700 : 400, fontSize: 14 }}>
      ₩{value.toLocaleString()}
    </span>
  </div>
)

const styles: Record<string, React.CSSProperties> = {
  pageTitle: { fontSize: 20, fontWeight: 700, marginBottom: 20 },
  empty: { color: '#888', padding: 40, textAlign: 'center' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 },
  card: {
    background: '#fff',
    border: '1px solid #e8eaed',
    borderRadius: 10,
    padding: 20,
    boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
  },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  accountType: { fontWeight: 700, fontSize: 15 },
  badge: { color: '#fff', fontSize: 11, padding: '2px 8px', borderRadius: 10, fontWeight: 600 },
  accountNumber: { color: '#555', fontSize: 13, marginBottom: 16, letterSpacing: 1 },
  balanceGrid: { borderTop: '1px solid #f0f0f0', paddingTop: 12, marginBottom: 16 },
  cardFooter: { display: 'flex', gap: 8 },
  actionBtn: {
    flex: 1,
    padding: '8px',
    border: 'none',
    borderRadius: 6,
    color: '#fff',
    fontWeight: 600,
    fontSize: 14,
    cursor: 'pointer',
  },
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999,
  },
  modal: {
    background: '#fff', borderRadius: 12, padding: 32, width: 360,
    boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
  },
  modalTitle: { fontSize: 18, fontWeight: 700, marginBottom: 8 },
  modalSub: { color: '#555', fontSize: 14, marginBottom: 16 },
  modalForm: { display: 'flex', flexDirection: 'column', gap: 12 },
  input: { padding: '10px 12px', borderRadius: 6, border: '1px solid #ccc', fontSize: 15 },
  modalBtns: { display: 'flex', gap: 8, marginTop: 4 },
  cancelBtn: { flex: 1, padding: '10px', background: '#f0f0f0', border: 'none', borderRadius: 6, fontWeight: 600, cursor: 'pointer' },
  confirmBtn: { flex: 1, padding: '10px', border: 'none', borderRadius: 6, color: '#fff', fontWeight: 700, cursor: 'pointer' },
  errorBox: { background: '#fff3f3', color: '#c00', border: '1px solid #fcc', borderRadius: 6, padding: '8px 12px', fontSize: 13 },
}

export default AccountPage
