import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { orderApi } from '@/api/orderApi'
import { OrderRequest } from '@/types/order'

/**
 * [Week 3 실습 포인트]
 * - useReducer 대신 useState로 시작 → Week 3에서 useReducer로 리팩터링 예정
 * - useMutation: 서버에 데이터 전송 + 성공 시 목록 캐시 무효화
 * - 로딩/에러 상태 UI 처리
 */
const OrderCreatePage = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [form, setForm] = useState<OrderRequest>({
    customerName: '',
    productName: '',
    quantity: 1,
    totalPrice: 0,
  })

  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof OrderRequest, string>>>({})

  const createMutation = useMutation({
    mutationFn: orderApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      navigate('/')
    },
  })

  // ── 유효성 검사 ─────────────────────────────────
  const validate = (): boolean => {
    const errors: Partial<Record<keyof OrderRequest, string>> = {}
    if (!form.customerName.trim()) errors.customerName = '고객명을 입력해주세요.'
    if (!form.productName.trim()) errors.productName = '상품명을 입력해주세요.'
    if (form.quantity < 1) errors.quantity = '수량은 1 이상이어야 합니다.'
    if (form.totalPrice <= 0) errors.totalPrice = '금액은 0보다 커야 합니다.'
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setForm((prev) => ({
      ...prev,
      [name]: name === 'quantity' || name === 'totalPrice' ? Number(value) : value,
    }))
    // 입력 시 해당 필드 에러 제거
    setFieldErrors((prev) => ({ ...prev, [name]: undefined }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    createMutation.mutate(form)
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>새 주문 등록</h2>

      {/* 서버 에러 표시 */}
      {createMutation.isError && (
        <div style={styles.serverError}>
          ⚠️ {(createMutation.error as Error).message}
        </div>
      )}

      <form onSubmit={handleSubmit} style={styles.form}>
        <Field
          label="고객명"
          name="customerName"
          type="text"
          value={form.customerName}
          onChange={handleChange}
          error={fieldErrors.customerName}
          placeholder="홍길동"
        />
        <Field
          label="상품명"
          name="productName"
          type="text"
          value={form.productName}
          onChange={handleChange}
          error={fieldErrors.productName}
          placeholder="노트북"
        />
        <Field
          label="수량"
          name="quantity"
          type="number"
          value={String(form.quantity)}
          onChange={handleChange}
          error={fieldErrors.quantity}
          placeholder="1"
        />
        <Field
          label="총 금액 (원)"
          name="totalPrice"
          type="number"
          value={String(form.totalPrice)}
          onChange={handleChange}
          error={fieldErrors.totalPrice}
          placeholder="100000"
        />

        <div style={styles.buttonRow}>
          <button
            type="button"
            style={styles.cancelBtn}
            onClick={() => navigate('/')}
          >
            취소
          </button>
          <button
            type="submit"
            style={{ ...styles.submitBtn, opacity: createMutation.isPending ? 0.7 : 1 }}
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? '등록 중...' : '주문 등록'}
          </button>
        </div>
      </form>
    </div>
  )
}

// ── 재사용 가능한 입력 필드 컴포넌트 ────────────────
interface FieldProps {
  label: string
  name: string
  type: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  error?: string
  placeholder?: string
}

const Field = ({ label, name, type, value, onChange, error, placeholder }: FieldProps) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
    <label style={styles.label}>{label}</label>
    <input
      name={name}
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      style={{ ...styles.input, borderColor: error ? '#d93025' : '#ccc' }}
      min={type === 'number' ? 0 : undefined}
    />
    {error && <span style={styles.errorText}>{error}</span>}
  </div>
)

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: 480,
    margin: '0 auto',
    background: '#fff',
    borderRadius: 8,
    padding: 32,
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  },
  title: { fontSize: 20, fontWeight: 700, marginBottom: 24 },
  serverError: {
    background: '#fce8e6',
    color: '#d93025',
    padding: '12px 16px',
    borderRadius: 4,
    marginBottom: 16,
    fontSize: 14,
  },
  form: { display: 'flex', flexDirection: 'column', gap: 18 },
  label: { fontSize: 13, fontWeight: 600, color: '#444' },
  input: {
    padding: '10px 12px',
    borderRadius: 4,
    border: '1px solid #ccc',
    fontSize: 14,
    outline: 'none',
    transition: 'border-color 0.2s',
  },
  errorText: { fontSize: 12, color: '#d93025' },
  buttonRow: {
    display: 'flex',
    gap: 12,
    marginTop: 8,
    justifyContent: 'flex-end',
  },
  cancelBtn: {
    padding: '10px 20px',
    background: '#fff',
    border: '1px solid #ccc',
    borderRadius: 4,
    fontSize: 14,
    color: '#444',
  },
  submitBtn: {
    padding: '10px 24px',
    background: '#1a73e8',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    fontSize: 14,
    fontWeight: 600,
  },
}

export default OrderCreatePage
