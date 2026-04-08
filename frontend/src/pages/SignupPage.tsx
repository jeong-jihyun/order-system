import { useState, FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { authApi, SignupRequest } from '@/api/authApi'
import { useAuth } from '@/context/AuthContext'

const SignupPage = () => {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [form, setForm] = useState<SignupRequest>({
    username: '',
    password: '',
    email: '',
    fullName: '',
  })

  const mutation = useMutation({
    mutationFn: () => authApi.signup(form),
    onSuccess: (data) => {
      login(data)
      navigate('/')
    },
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((p) => ({ ...p, [e.target.name]: e.target.value }))
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    mutation.mutate()
  }

  return (
    <div style={styles.wrap}>
      <div style={styles.card}>
        <h1 style={styles.title}>🏦 Exchange System</h1>
        <p style={styles.subtitle}>회원가입</p>

        {mutation.isError && (
          <div style={styles.errorBox}>⚠️ {(mutation.error as Error).message}</div>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <Field label="사용자명 (영문+숫자)" name="username" value={form.username} onChange={handleChange} placeholder="user123" />
          <Field label="비밀번호 (8자 이상)" name="password" type="password" value={form.password} onChange={handleChange} placeholder="••••••••" />
          <Field label="이메일" name="email" type="email" value={form.email} onChange={handleChange} placeholder="user@example.com" />
          <Field label="이름" name="fullName" value={form.fullName} onChange={handleChange} placeholder="홍길동" />

          <button
            type="submit"
            style={{ ...styles.btn, opacity: mutation.isPending ? 0.7 : 1 }}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? '가입 중...' : '회원가입'}
          </button>
        </form>

        <p style={styles.footer}>
          이미 계정이 있으신가요?{' '}
          <Link to="/login" style={styles.link}>로그인</Link>
        </p>
      </div>
    </div>
  )
}

interface FieldProps {
  label: string
  name: string
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  placeholder?: string
  type?: string
}

const Field = ({ label, name, value, onChange, placeholder, type = 'text' }: FieldProps) => (
  <div>
    <label style={styles.label}>{label}</label>
    <input
      style={styles.input}
      type={type}
      name={name}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      required
    />
  </div>
)

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#f0f4f8',
  },
  card: {
    background: '#fff',
    borderRadius: 12,
    padding: '48px 40px',
    width: 380,
    boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
  },
  title: { textAlign: 'center', fontSize: 24, fontWeight: 700, marginBottom: 4 },
  subtitle: { textAlign: 'center', color: '#666', marginBottom: 28 },
  form: { display: 'flex', flexDirection: 'column', gap: 12 },
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: '#333', marginBottom: 4 },
  input: {
    width: '100%',
    padding: '10px 12px',
    borderRadius: 6,
    border: '1px solid #ccc',
    fontSize: 14,
    boxSizing: 'border-box',
  },
  btn: {
    marginTop: 8,
    padding: '12px',
    background: '#34a853',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    fontWeight: 700,
    fontSize: 15,
    cursor: 'pointer',
    width: '100%',
  },
  errorBox: {
    background: '#fff3f3',
    color: '#c00',
    border: '1px solid #fcc',
    borderRadius: 6,
    padding: '10px 14px',
    marginBottom: 16,
    fontSize: 13,
  },
  footer: { textAlign: 'center', marginTop: 20, fontSize: 13, color: '#666' },
  link: { color: '#1a73e8', fontWeight: 600 },
}

export default SignupPage
