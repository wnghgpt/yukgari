import type { OhlcvBar, StockInfo, WatchlistItem, RankingItem, JournalTrade } from '../types'

const BASE = '/api'

async function get<T>(path: string, params: Record<string, string | number> = {}): Promise<T> {
  const qs = new URLSearchParams(params as Record<string, string>).toString()
  const res = await fetch(`${BASE}${path}${qs ? '?' + qs : ''}`)
  if (!res.ok) throw new Error(`${res.status} ${path}`)
  return res.json()
}

export const api = {
  ohlcv: (symbol: string, count = 900, period = 'D') =>
    get<OhlcvBar[]>('/ohlcv', { symbol, count, period }),

  stockInfo: (q: string) =>
    get<StockInfo>('/stock-info', { q }),

  price: (symbol: string) =>
    get<{ symbol: string; price: number | null; prev_close: number | null }>('/price', { symbol }),

  search: (q: string) =>
    get<StockInfo[]>('/search', { q }),

  rankingMarcap: () =>
    get<RankingItem[]>('/ranking/marcap'),

  rankingTrading: () =>
    get<RankingItem[]>('/ranking/trading'),

  rankingUsMarcap: () =>
    get<RankingItem[]>('/ranking/us-marcap'),

  rankingUsTrading: () =>
    get<RankingItem[]>('/ranking/us-trading'),

  watchlist: (uid: string) =>
    get<WatchlistItem[]>('/watchlist', { uid }),

  addWatchlist: (body: { stock_code: string; stock_name: string; market_type: string }, uid: string) =>
    fetch(`/api/watchlist?uid=${encodeURIComponent(uid)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json() }),

  removeWatchlist: (symbol: string, uid: string) =>
    fetch(`/api/watchlist/${symbol}?uid=${encodeURIComponent(uid)}`, { method: 'DELETE' })
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json() }),

  journal: (uid: string) =>
    get<JournalTrade[]>('/journal', { uid }),

  addJournal: (body: Record<string, unknown>, uid: string) =>
    fetch(`/api/journal?uid=${encodeURIComponent(uid)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json() }),

  updateJournal: (id: string, body: Record<string, unknown>, uid: string) =>
    fetch(`/api/journal/${id}?uid=${encodeURIComponent(uid)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json() }),

  deleteJournal: (id: string, uid: string) =>
    fetch(`/api/journal/${id}?uid=${encodeURIComponent(uid)}`, { method: 'DELETE' })
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json() }),

  indicators: (symbol: string) =>
    get<{
      vol_ratio: number
      rsi: number | null
      alignment: string | null
      ma_order: string | null
      above_ma: { period: number; pct: number; slope: string } | null
      below_ma: { period: number; pct: number; slope: string } | null
      all_mas: Record<string, { pct: number; slope: string }>
    }>('/indicators', { symbol }),
}

export async function fetchWatchlistPrices(items: WatchlistItem[]): Promise<WatchlistItem[]> {
  const results = await Promise.allSettled(
    items.map(item => api.price(item.symbol))
  )
  return items.map((item, i) => {
    const r = results[i]
    if (r.status === 'fulfilled' && r.value.price != null) {
      return { ...item, price: r.value.price }
    }
    return item
  })
}
