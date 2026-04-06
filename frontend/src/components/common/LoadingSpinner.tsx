/**
 * [Week 3 - 로딩 처리 실습]
 * 공통 로딩 스피너 컴포넌트
 */
const LoadingSpinner = ({ message = '불러오는 중...' }: { message?: string }) => {
  return (
    <div style={styles.container}>
      <div style={styles.spinner} />
      <p style={styles.text}>{message}</p>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 48,
    gap: 16,
  },
  spinner: {
    width: 40,
    height: 40,
    border: '4px solid #e0e0e0',
    borderTopColor: '#1a73e8',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  text: {
    color: '#666',
    fontSize: 14,
  },
}

// CSS 애니메이션을 동적으로 주입
const style = document.createElement('style')
style.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`
document.head.appendChild(style)

export default LoadingSpinner
