import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '../../store'
import { useWatchlist } from '../../hooks/useWatchlist'
import { usePriceSocket } from '../../hooks/usePriceSocket'
import { api } from '../../api/stock'

type MarketFilter = 'all' | 'KR' | 'US'

const FILTERS: { id: MarketFilter; label: string }[] = [
  { id: 'all', label: '전체' },
  { id: 'KR',  label: '🇰🇷 국내' },
  { id: 'US',  label: '🇺🇸 해외' },
]

interface Props {
  currentSymbol: string
}

export function WatchlistTab({ currentSymbol }: Props) {
  const [query, setQuery] = useState('')
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [filter, setFilter] = useState<MarketFilter>('KR')
  const wrapRef = useRef<HTMLDivElement>(null)

  const { setSymbol, livePrices, setLivePrice, prevCloses, setPrevClose } = useAppStore()
  const { watchlist, isInWatchlist, toggle } = useWatchlist()

  const { subscribe } = usePriceSocket((sym, price) => setLivePrice(sym, price))
  useEffect(() => {
    if (!watchlist.length) return
    watchlist.forEach(item => subscribe(item.symbol))
    const missing = watchlist
      .filter(item => prevCloses[item.symbol] == null || livePrices[item.symbol] == null)
      .map(item => item.symbol)
    if (missing.length) {
      api.prices(missing).then(results => {
        results.forEach(r => {
          if (r.prev_close != null) setPrevClose(r.symbol, r.prev_close)
          if (r.price != null) setLivePrice(r.symbol, r.price)
        })
      }).catch(() => {})
    }
  }, [watchlist, subscribe]) // eslint-disable-line react-hooks/exhaustive-deps

  const { data: searchResults = [] } = useQuery({
    queryKey: ['search', query],
    queryFn: () => api.search(query),
    enabled: query.length >= 1,
    staleTime: 10_000,
  })

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node))
        setDropdownOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const isOverseas = (symbol: string) => !/^\d+$/.test(symbol)

  const formatPrice = (symbol: string, price?: number) => {
    if (price == null) return '—'
    return isOverseas(symbol) ? `$${price.toFixed(2)}` : price.toLocaleString()
  }

  const filtered = watchlist.filter(item => {
    if (filter === 'all') return true
    const mtype = item.market_type ?? (isOverseas(item.symbol) ? 'US' : 'KR')
    return mtype === filter
  })

  return (
    <div className="watchlist-tab">
      {/* 검색창 */}
      <div ref={wrapRef} className="wl-search-wrap">
        <input
          className="wl-search-input"
          placeholder="🔍 종목 검색..."
          value={query}
          onChange={e => { setQuery(e.target.value); setDropdownOpen(true) }}
          onFocus={() => query && setDropdownOpen(true)}
        />
        {dropdownOpen && searchResults.length > 0 && (
          <ul className="wl-dropdown">
            {searchResults.map(r => (
              <li key={r.symbol} className="wl-dropdown-item">
                <span
                  className="wl-dropdown-name"
                  onClick={() => {
                    setSymbol(r.symbol, r.name)
                    setDropdownOpen(false)
                    setQuery('')
                  }}
                >
                  <span className="wl-flag">{isOverseas(r.symbol) ? '🇺🇸' : '🇰🇷'}</span>
                  <span className="wl-dname">{r.name}</span>
                  <span className="wl-dcode">{r.symbol}</span>
                </span>
                <button
                  className={`wl-star-btn ${isInWatchlist(r.symbol) ? 'starred' : ''}`}
                  onClick={e => { e.stopPropagation(); toggle(r.symbol, r.name) }}
                >
                  {isInWatchlist(r.symbol) ? '⭐' : '☆'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 국내/해외 필터 */}
      <div className="wl-filter-bar">
        {FILTERS.map(f => (
          <button
            key={f.id}
            className={`wl-filter-btn ${filter === f.id ? 'active' : ''}`}
            onClick={() => setFilter(f.id)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* 관심종목 목록 */}
      <div className="wl-list">
        {filtered.length === 0 && (
          <div className="wl-empty">
            {watchlist.length === 0 ? '검색 후 ☆로 추가' : '해당 종목 없음'}
          </div>
        )}
        {filtered.map(item => {
          const price     = livePrices[item.symbol] ?? item.price
          const prevClose = prevCloses[item.symbol]
          const changePct = price != null && prevClose != null && prevClose > 0
            ? ((price - prevClose) / prevClose) * 100
            : null
          return (
            <div
              key={item.symbol}
              className={`wl-item ${item.symbol === currentSymbol ? 'active' : ''}`}
              onClick={() => setSymbol(item.symbol, item.name)}
            >
              <span className="wl-flag">{isOverseas(item.symbol) ? '🇺🇸' : '🇰🇷'}</span>
              <div className="wl-item-info">
                <span className="wl-item-name">{item.name}</span>
                <span className="wl-item-code">{item.symbol}</span>
              </div>
              <div className="wl-item-right">
                <div className="wl-price-col">
                  <span className="wl-item-price">{formatPrice(item.symbol, price)}</span>
                  {changePct != null && (
                    <span className={`wl-change ${changePct >= 0 ? 'up' : 'down'}`}>
                      {changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%
                    </span>
                  )}
                </div>
                <button
                  className="wl-star-btn starred"
                  onClick={e => { e.stopPropagation(); toggle(item.symbol, item.name) }}
                >
                  ⭐
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
