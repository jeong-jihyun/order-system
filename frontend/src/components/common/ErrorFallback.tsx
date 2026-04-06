/**
 * [Week 3 - 에러 처리 실습]
 * TanStack Query의 isError 상태 또는 ErrorBoundary에서 사용하는 공통 에러 UI
 */
interface ErrorFallbackProps {
  error: Error
  resetErrorBoundary?: () => void
}

const ErrorFallback = ({ error, resetErrorBoundary }: ErrorFallbackProps) => {
  return (
    <div style={styles.container}>
      <div style={styles.icon}>⚠️</div>
      <h3 style={styles.title}>오류가 발생했습니다</h3>
      <p style={styles.message}>{error.message}</p>
      {resetErrorBoundary && (
        <button style={styles.button} onClick={resetErrorBoundary}>
          다시 시도
        </button>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: 48,
    gap: 12,
    background: '#fff',
    borderRadius: 8,
    border: '1px solid #fce8e6',
  },
  icon: { fontSize: 40 },
  title: { fontSize: 18, color: '#d93025' },
  message: { fontSize: 14, color: '#666', maxWidth: 400, textAlign: 'center' },
  button: {
    marginTop: 8,
    padding: '8px 20px',
    background: '#1a73e8',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    fontSize: 14,
  },
}

export default ErrorFallback
