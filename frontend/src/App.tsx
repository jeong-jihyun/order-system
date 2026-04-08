import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import LoginPage from '@/pages/LoginPage'
import SignupPage from '@/pages/SignupPage'
import OrderListPage from '@/pages/OrderListPage'
import OrderCreatePage from '@/pages/OrderCreatePage'
import AccountPage from '@/pages/AccountPage'
import MarketPage from '@/pages/MarketPage'
import SettlementPage from '@/pages/SettlementPage'
import OrderBookPage from '@/pages/OrderBookPage'

// 인증이 필요한 라우트 — 미로그인 시 /login 으로 리다이렉트
const PrivateRoute = ({ children }: { children: React.ReactNode }) => {
  const { isLoggedIn } = useAuth()
  const location = useLocation()
  if (!isLoggedIn) return <Navigate to="/login" state={{ from: location }} replace />
  return <>{children}</>
}

// 로그인된 상태에서 /login, /signup 접근 시 홈으로
const PublicOnlyRoute = ({ children }: { children: React.ReactNode }) => {
  const { isLoggedIn } = useAuth()
  if (isLoggedIn) return <Navigate to="/" replace />
  return <>{children}</>
}

const NAV_ITEMS = [
  { to: '/', label: '📋 주문 목록' },
  { to: '/orders/new', label: '➕ 새 주문' },
  { to: '/accounts', label: '💳 계좌' },
  { to: '/market', label: '📈 시세' },
  { to: '/orderbook', label: '📊 호가창' },
  { to: '/settlements', label: '🧾 정산' },
]

const AppLayout = () => {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <div style={{ minHeight: '100vh', background: '#f0f4f8' }}>
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <Link to="/" style={styles.logo}>🏦 Exchange System</Link>
          <nav style={styles.nav}>
            {NAV_ITEMS.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                style={{
                  ...styles.navLink,
                  ...(location.pathname === to ? styles.navLinkActive : {}),
                }}
              >
                {label}
              </Link>
            ))}
          </nav>
          <div style={styles.userArea}>
            <span style={styles.username}>{user?.username}</span>
            <button style={styles.logoutBtn} onClick={logout}>로그아웃</button>
          </div>
        </div>
      </header>
      <main style={styles.main}>
        <Routes>
          <Route path="/" element={<OrderListPage />} />
          <Route path="/orders/new" element={<OrderCreatePage />} />
          <Route path="/accounts" element={<AccountPage />} />
          <Route path="/market" element={<MarketPage />} />
          <Route path="/orderbook" element={<OrderBookPage />} />
          <Route path="/settlements" element={<SettlementPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<PublicOnlyRoute><LoginPage /></PublicOnlyRoute>} />
          <Route path="/signup" element={<PublicOnlyRoute><SignupPage /></PublicOnlyRoute>} />
          <Route path="/*" element={<PrivateRoute><AppLayout /></PrivateRoute>} />
        </Routes>
      </Router>
    </AuthProvider>
  )
}

const styles: Record<string, React.CSSProperties> = {
  header: {
    background: '#1a1f2e',
    padding: '0 24px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
    position: 'sticky',
    top: 0,
    zIndex: 100,
  },
  headerInner: {
    maxWidth: 1280,
    margin: '0 auto',
    display: 'flex',
    alignItems: 'center',
    gap: 24,
    height: 56,
  },
  logo: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 800,
    textDecoration: 'none',
    whiteSpace: 'nowrap',
    marginRight: 12,
  },
  nav: {
    display: 'flex',
    gap: 4,
    flex: 1,
    flexWrap: 'wrap',
  },
  navLink: {
    color: 'rgba(255,255,255,0.7)',
    textDecoration: 'none',
    fontWeight: 500,
    fontSize: 13,
    padding: '6px 10px',
    borderRadius: 6,
    transition: 'all 0.15s',
  },
  navLinkActive: {
    color: '#fff',
    background: 'rgba(255,255,255,0.15)',
  },
  userArea: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginLeft: 'auto',
    whiteSpace: 'nowrap',
  },
  username: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 13,
    fontWeight: 600,
  },
  logoutBtn: {
    padding: '5px 12px',
    background: 'rgba(255,255,255,0.1)',
    color: '#fff',
    border: '1px solid rgba(255,255,255,0.2)',
    borderRadius: 6,
    fontSize: 12,
    cursor: 'pointer',
    fontWeight: 600,
  },
  main: {
    maxWidth: 1280,
    margin: '28px auto',
    padding: '0 24px',
  },
}

export default App
