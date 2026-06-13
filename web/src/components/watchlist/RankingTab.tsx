import { useState, useEffect, useRef } from 'react'
import { useAppStore } from '../../store'
import { useWatchlist } from '../../hooks/useWatchlist'
import { api } from '../../api/stock'
import type { RankingItem } from '../../types'

interface PriceInfo {
  price: number | null
  prevClose: number | null
}

interface Props {
  data: RankingItem[]
  loading: boolean
  valueHeader: string
  market: 'KR' | 'US'
}

export function RankingTab({ data, loading, valueHeader, market }: Props) {
  const { setSymbol, symbol: currentSymbol, livePrices, prevCloses } = useAppStore()
  const { isInWatchlist, toggle } = useWatchlist()
  const [prices, setPrices] = useState<Record<string, PriceInfo>>({})
  const [fetching, setFetching] = useState(false)
  const fetchedKeyRef = useRef('')

  const fetchPrices = async (items: RankingItem[]) => {
    if (items.length === 0) return
    setFetching(true)
    const results = await Promise.allSettled(items.map(item => api.price(item.symbol)))
    const map: Record<string, PriceInfo> = {}
    items.forEach((item, i) => {
      const r = results[i]
      if (r.status === 'fulfilled') {
        map[item.symbol] = { price: r.value.price, prevClose: r.value.prev_close }
      }
    })
    setPrices(map)
    setFetching(false)
  }

  useEffect(() => {
    if (data.length === 0) return
    const key = data[0]?.symbol + data.length
    if (key === fetchedKeyRef.current) return
    fetchedKeyRef.current = key
    setPrices({})
    fetchPrices(data)
  }, [data]) // eslint-disable-line react-hooks/exhaustive-deps

  const getPrice = (symbol: string): PriceInfo => {
    // 관심종목에 있어 WebSocket으로 실시간 수신 중인 경우 우선 사용
    const live = livePrices[symbol]
    const prev = prevCloses[symbol]
    if (live != null) return { price: live, prevClose: prev ?? prices[symbol]?.prevClose ?? null }
    return prices[symbol] ?? { price: null, prevClose: null }
  }

  const fmtPrice = (symbol: string, price: number) =>
    market === 'US' ? `$${price.toFixed(2)}` : price.toLocaleString()

  if (loading && data.length === 0) {
    return <div className="wl-loading">불러오는 중...</div>
  }

  return (
    <div className="ranking-tab">
      <div className="ranking-header">
        <span className="rh-rank">#</span>
        <span className="rh-name">종목</span>
        <span className="rh-price">{fetching ? '조회 중…' : '현재가'}</span>
        <span className="rh-star" />
      </div>
      <div className="ranking-list">
        {data.map(item => {
          const { price, prevClose } = getPrice(item.symbol)
          const changePct = price != null && prevClose != null && prevClose > 0
            ? (price - prevClose) / prevClose * 100
            : null
          return (
            <div
              key={item.symbol}
              className={`ranking-item ${item.symbol === currentSymbol ? 'active' : ''}`}
              onClick={() => setSymbol(item.symbol, item.name)}
            >
              <span className="r-rank">{item.rank}</span>
              <div className="r-info">
                <span className="r-name">{item.name}</span>
                <span className="r-code">{item.symbol}</span>
              </div>
              <div className="r-price-col">
                {price != null
                  ? <span className="r-price">{fmtPrice(item.symbol, price)}</span>
                  : <span className="r-price r-price-empty">—</span>
                }
                {changePct != null && (
                  <span className={`r-change ${changePct >= 0 ? 'up' : 'down'}`}>
                    {changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%
                  </span>
                )}
              </div>
              <button
                className={`wl-star-btn ${isInWatchlist(item.symbol) ? 'starred' : ''}`}
                onClick={e => { e.stopPropagation(); toggle(item.symbol, item.name) }}
              >
                {isInWatchlist(item.symbol) ? '⭐' : '☆'}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
