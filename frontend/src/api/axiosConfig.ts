import axios from 'axios'

/**
 * Axios 기본 인스턴스
 * - baseURL: vite.config.ts proxy를 통해 /api → Spring :8080/api
 * - 인터셉터로 공통 에러 처리
 */
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10_000,
})

// 응답 인터셉터 — API 레벨 오류 처리
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.message ?? error.message ?? '알 수 없는 오류가 발생했습니다.'
    return Promise.reject(new Error(message))
  },
)
