import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import AppBar from '@mui/material/AppBar'
import Toolbar from '@mui/material/Toolbar'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import Box from '@mui/material/Box'
import Tabs from '@mui/material/Tabs'
import Tab from '@mui/material/Tab'
import Container from '@mui/material/Container'
import Chip from '@mui/material/Chip'
import AccountBalanceIcon from '@mui/icons-material/AccountBalance'
import LoginPage from '@/pages/LoginPage'
import SignupPage from '@/pages/SignupPage'
import OrderListPage from '@/pages/OrderListPage'
import OrderCreatePage from '@/pages/OrderCreatePage'
import AccountPage from '@/pages/AccountPage'
import MarketPage from '@/pages/MarketPage'
import SettlementPage from '@/pages/SettlementPage'
import OrderBookPage from '@/pages/OrderBookPage'
import PortfolioPage from '@/pages/PortfolioPage'

const PrivateRoute = ({ children }: { children: React.ReactNode }) => {
  const { isLoggedIn } = useAuth()
  const location = useLocation()
  if (!isLoggedIn) return <Navigate to="/login" state={{ from: location }} replace />
  return <>{children}</>
}

const PublicOnlyRoute = ({ children }: { children: React.ReactNode }) => {
  const { isLoggedIn } = useAuth()
  if (isLoggedIn) return <Navigate to="/" replace />
  return <>{children}</>
}

const NAV_ITEMS = [
  { to: '/',              label: '주문' },
  { to: '/orders/new',   label: '새 주문' },
  { to: '/accounts',     label: '계좌' },
  { to: '/portfolio',    label: '포트폴리오' },
  { to: '/market',       label: '시세' },
  { to: '/orderbook',    label: '호가창' },
  { to: '/settlements',  label: '정산' },
]

const AppLayout = () => {
  const { user, logout } = useAuth()
  const location = useLocation()

  const tabIdx = NAV_ITEMS.findIndex((n) => n.to === location.pathname)

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="sticky" sx={{ bgcolor: '#1e222d', boxShadow: '0 1px 0 #2a2e39' }}>
        <Toolbar sx={{ maxWidth: 1400, width: '100%', mx: 'auto', px: 2, gap: 2 }}>
          <Typography
            component={Link}
            to="/"
            variant="h6"
            sx={{
              fontWeight: 800,
              color: '#d1d4dc',
              textDecoration: 'none',
              mr: 3,
              fontSize: 17,
              whiteSpace: 'nowrap',
            }}
          >
            가상 증권 거래서
          </Typography>

          <Tabs
            value={tabIdx >= 0 ? tabIdx : false}
            sx={{
              flex: 1,
              minHeight: 48,
              '& .MuiTab-root': {
                minHeight: 48,
                color: '#787b86',
                fontSize: 13,
                py: 0,
                '&.Mui-selected': { color: '#d1d4dc' },
              },
              '& .MuiTabs-indicator': { bgcolor: '#2962ff', height: 2 },
            }}
          >
            {NAV_ITEMS.map(({ to, label }) => (
              <Tab
                key={to}
                label={label}
                component={Link}
                to={to}
              />
            ))}
          </Tabs>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, ml: 'auto' }}>
            <Chip
              label={user?.username}
              size="small"
              sx={{ bgcolor: '#2a2e39', color: '#d1d4dc', fontWeight: 600, fontSize: 12 }}
            />
            <Button
              size="small"
              variant="outlined"
              onClick={logout}
              sx={{
                color: '#787b86',
                borderColor: '#363a45',
                fontSize: 12,
                '&:hover': { borderColor: '#787b86', bgcolor: 'rgba(255,255,255,0.04)' },
              }}
            >
              로그아웃
            </Button>
          </Box>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Routes>
          <Route path="/" element={<OrderListPage />} />
          <Route path="/orders/new" element={<OrderCreatePage />} />
          <Route path="/accounts" element={<AccountPage />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/market" element={<MarketPage />} />
          <Route path="/orderbook" element={<OrderBookPage />} />
          <Route path="/settlements" element={<SettlementPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Container>
    </Box>
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

export default App
