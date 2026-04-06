import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import OrderListPage from '@/pages/OrderListPage'
import OrderCreatePage from '@/pages/OrderCreatePage'

function App() {
  return (
    <Router>
      <div style={{ minHeight: '100vh' }}>
        {/* 헤더 */}
        <header style={styles.header}>
          <div style={styles.headerInner}>
            <h1 style={styles.logo}>🛒 주문 관리 시스템</h1>
            <nav style={styles.nav}>
              <Link to="/" style={styles.navLink}>주문 목록</Link>
              <Link to="/orders/new" style={styles.navLink}>새 주문</Link>
            </nav>
          </div>
        </header>

        {/* 본문 */}
        <main style={styles.main}>
          <Routes>
            <Route path="/" element={<OrderListPage />} />
            <Route path="/orders/new" element={<OrderCreatePage />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

const styles: Record<string, React.CSSProperties> = {
  header: {
    background: '#1a73e8',
    padding: '0 24px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
  },
  headerInner: {
    maxWidth: 960,
    margin: '0 auto',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    height: 60,
  },
  logo: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 700,
  },
  nav: {
    display: 'flex',
    gap: 20,
  },
  navLink: {
    color: '#fff',
    textDecoration: 'none',
    fontWeight: 500,
    fontSize: 15,
  },
  main: {
    maxWidth: 960,
    margin: '32px auto',
    padding: '0 24px',
  },
}

export default App
