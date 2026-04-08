import { useState, FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { authApi } from '@/api/authApi'
import { useAuth } from '@/context/AuthContext'

const LoginPage = () => {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [form, setForm] = useState({ username: '', password: '' })

  const mutation = useMutation({
    mutationFn: () => authApi.login(form),
    onSuccess: (data) => {
      login(data)
      navigate('/')
    },
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!form.username || !form.password) return
    mutation.mutate()
  }

  return (
    <div style={styles.wrap}>
      <div style={styles.card}>
        <h1 style={styles.title}>🏦 Exchange System</h1>
        <p style={styles.subtitle}>로그인</p>

        {mutation.isError && (
          <div style={styles.errorBox}>⚠️ {(mutation.error as Error).message}</div>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <label style={styles.label}>사용자명</label>
          <input
            style={styles.input}
            type="text"
            autoComplete="username"
            value={form.username}
            onChange={(e) => setForm((p) => ({ ...p, username: e.target.value }))}
            placeholder="username"
            required
          />

          <label style={styles.label}>비밀번호</label>
          <input
            style={styles.input}
            type="password"
            autoComplete="current-password"
            value={form.password}
            onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))}
            placeholder="••••••••"
            required
          />

          <button
            type="submit"
            style={{ ...styles.btn, opacity: mutation.isPending ? 0.7 : 1 }}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? '로그인 중...' : '로그인'}
          </button>
        </form>

        <p style={styles.footer}>
          계정이 없으신가요?{' '}
          <Link to="/signup" style={styles.link}>
            회원가입
          </Link>
        </p>
      </div>
    </div>
  )
}

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
    width: 360,
    boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
  },
  title: { textAlign: 'center', fontSize: 24, fontWeight: 700, marginBottom: 4 },
  subtitle: { textAlign: 'center', color: '#666', marginBottom: 28 },
  form: { display: 'flex', flexDirection: 'column', gap: 8 },
  label: { fontSize: 13, fontWeight: 600, color: '#333' },
  input: {
    padding: '10px 12px',
    borderRadius: 6,
    border: '1px solid #ccc',
    fontSize: 14,
    marginBottom: 8,
    outline: 'none',
  },
  btn: {
    marginTop: 8,
    padding: '12px',
    background: '#1a73e8',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    fontWeight: 700,
    fontSize: 15,
    cursor: 'pointer',
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

export default LoginPage
