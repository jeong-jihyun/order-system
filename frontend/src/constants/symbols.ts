export interface SymbolInfo {
  code: string
  name: string
}

export const SYMBOL_MAP: Record<string, SymbolInfo> = {
  AAPL:  { code: 'AAPL',  name: '애플' },
  TSLA:  { code: 'TSLA',  name: '테슬라' },
  NVDA:  { code: 'NVDA',  name: '엔비디아' },
  MSFT:  { code: 'MSFT',  name: '마이크로소프트' },
  GOOGL: { code: 'GOOGL', name: '알파벳(구글)' },
}

export const SYMBOLS = Object.keys(SYMBOL_MAP)
