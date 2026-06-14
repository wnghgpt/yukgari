export interface OhlcvBar {
  Date: string
  Open: number
  High: number
  Low: number
  Close: number
  Volume: number
}

export interface StockInfo {
  name: string
  symbol: string
}

export interface PriceMessage {
  symbol: string
  price: number
}

export interface WatchlistItem {
  symbol: string
  name: string
  market_type?: 'KR' | 'US'
  price?: number
}

export type Period = 'D' | 'W'

export interface RankingItem {
  rank: number
  symbol: string
  name: string
  value: number
  value_label: string
  price?: number | null
  change_pct?: number | null
}

export type SidebarTab = 'watchlist' | 'marcap' | 'trading'

export interface ScenarioPoint {
  barOffset: number   // 0 = 마지막 봉, 양수 = 미래 봉
  price: number
}

export interface ScenarioEntry {
  barOffset: number
  price: number
  nth: number
}

export interface DrawnLine {
  id: string
  type: 'horizontal' | 'segment'
  color: string
  price?: number
  barOffset1?: number; price1?: number
  barOffset2?: number; price2?: number
}

export interface ScenarioData {
  points: ScenarioPoint[]
  entries: ScenarioEntry[]
  resistPrice: number
  supportPrice?: number
  targetPrice: number
  stopLoss: number
  avgPrice: number
}

export interface JournalTrade {
  id: string
  date: string
  exit_date?: string
  ticker: string
  name?: string
  pattern: string
  stages: number
  channel_top?: number
  channel_bottom?: number
  entry1_price?: number; entry1_weight?: number
  entry2_price?: number; entry2_weight?: number
  entry3_price?: number; entry3_weight?: number
  entry4_price?: number; entry4_weight?: number
  stop_loss?: number
  target_price?: number
  result: string
  exit1_price?: number; exit1_qty?: number
  exit2_price?: number; exit2_qty?: number
  rebound_after_stop?: boolean
  rebound_price?: number
  memo?: string
  created_at: string
}
