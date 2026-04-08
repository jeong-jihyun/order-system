import { createTheme } from '@mui/material/styles'

// TradingView 계열 다크 거래 테마
export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary:   { main: '#2962ff' },
    secondary: { main: '#ff6d00' },
    success:   { main: '#26a69a' },   // BUY 색상
    error:     { main: '#ef5350' },   // SELL 색상
    warning:   { main: '#f5a623' },
    background: {
      default: '#131722',
      paper:   '#1e222d',
    },
    text: {
      primary:   '#d1d4dc',
      secondary: '#787b86',
      disabled:  '#4c525e',
    },
    divider: '#2a2e39',
  },
  shape: { borderRadius: 6 },
  typography: {
    fontFamily: '"Noto Sans KR", "Roboto", "Helvetica", "Arial", sans-serif',
    fontSize: 13,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { backgroundColor: '#131722', scrollbarColor: '#2a2e39 #1e222d' },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none', border: '1px solid #2a2e39' },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: { background: '#131722', fontWeight: 700, fontSize: 12, color: '#787b86' },
        body: { borderColor: '#2a2e39', fontSize: 13 },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { textTransform: 'none', fontWeight: 600 },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: { textTransform: 'none', fontWeight: 600, fontSize: 14 },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600, fontSize: 11 },
      },
    },
    MuiTextField: {
      defaultProps: { size: 'small', variant: 'outlined' },
    },
  },
})
