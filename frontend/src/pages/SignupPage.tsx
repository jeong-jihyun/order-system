import { useState, FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { authApi, SignupRequest } from '@/api/authApi'
import { useAuth } from '@/context/AuthContext'
import Box from '@mui/material/Box'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import TextField from '@mui/material/TextField'
import Button from '@mui/material/Button'
import Alert from '@mui/material/Alert'
import AccountBalanceIcon from '@mui/icons-material/AccountBalance'

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
    <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#131722' }}>
      <Paper sx={{ p: 5, width: 400, bgcolor: '#1e222d', border: '1px solid #2a2e39' }}>
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <AccountBalanceIcon sx={{ fontSize: 40, color: '#2962ff', mb: 1 }} />
          <Typography variant="h5" sx={{ fontWeight: 800, color: '#d1d4dc' }}>Exchange System</Typography>
          <Typography variant="body2" sx={{ color: '#787b86', mt: 0.5 }}>회원가입</Typography>
        </Box>

        {mutation.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {(mutation.error as Error).message}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <TextField fullWidth label="사용자명 (영문+숫자)" name="username" value={form.username} onChange={handleChange} required sx={{ mb: 2 }} />
          <TextField fullWidth label="비밀번호 (8자 이상)" name="password" type="password" value={form.password} onChange={handleChange} required sx={{ mb: 2 }} />
          <TextField fullWidth label="이메일" name="email" type="email" value={form.email} onChange={handleChange} required sx={{ mb: 2 }} />
          <TextField fullWidth label="이름" name="fullName" value={form.fullName} onChange={handleChange} required sx={{ mb: 3 }} />
          <Button
            type="submit"
            fullWidth
            variant="contained"
            color="success"
            size="large"
            disabled={mutation.isPending}
            sx={{ py: 1.3, fontWeight: 700, fontSize: 15 }}
          >
            {mutation.isPending ? '가입 중...' : '회원가입'}
          </Button>
        </form>

        <Typography variant="body2" sx={{ textAlign: 'center', mt: 2.5, color: '#787b86' }}>
          이미 계정이 있으신가요?{' '}
          <Link to="/login" style={{ color: '#2962ff', fontWeight: 600 }}>로그인</Link>
        </Typography>
      </Paper>
    </Box>
  )
}

export default SignupPage
