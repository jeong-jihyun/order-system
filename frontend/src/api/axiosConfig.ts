import axios from 'axios'

const TOKEN_KEY = 'auth_token'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10_000,
})

// 요청 인터셉터 — localStorage 토큰을 Authorization 헤더에 자동 주입
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 모든 POST/PUT 요청의 body를 JSON.stringify로 강제 직렬화
apiClient.interceptors.request.use((config) => {
  if (
    config.data &&
    (config.method === 'post' || config.method === 'put' || config.method === 'patch') &&
    config.headers['Content-Type'] === 'application/json' &&
    typeof config.data !== 'string'
  ) {
    config.data = JSON.stringify(config.data)
  }
  return config
})

// 응답 인터셉터 — API 레벨 오류 처리 + 401 시 로그인 페이지로 이동
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      window.location.href = '/login'
    }
    const message =
      error.response?.data?.message ?? error.message ?? '알 수 없는 오류가 발생했습니다.'
    return Promise.reject(new Error(message))
  },
)
