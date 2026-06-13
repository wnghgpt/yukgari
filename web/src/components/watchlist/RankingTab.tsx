import { useAppStore } from '../../store'
import { useWatchlist } from '../../hooks/useWatchlist'
import type { RankingItem } from '../../types'

interface Props {
  data: RankingItem[]
  loading: boolean
  market: 'KR' | 'US'
}

export function RankingTab({ data, loading, market }: Props) {
  const { setSymbol, symbol: currentSymbol, livePrices, prevCloses } = useAppStore()
  const { isInWatchlist, toggle } = useWatchlist()

  const getDisplayPrice = (item: RankingItem): { price: number | null; changePct: number | null } => {
    const live = livePrices[item.symbol]
    if (live != null) {
      const prev = prevCloses[item.symbol]
      const changePct = prev != null && prev > 0
        ? (live - prev) / prev * 100
        : (item.change_pct ?? null)
      return { price: live, changePct }
    }
    return {
      price: item.price ?? null,
      changePct: item.change_pct ?? null,
    }
  }

  const fmtPrice = (price: number) =>
    market === 'US' ? `$${price.toFixed(2)}` : price.toLocaleString()

  if (loading && data.length === 0) {
    return <div className="wl-loading">불러오는 중...</div>
  }

  return (
    <div className="ranking-tab">
      <div className="ranking-header">
        <span className="rh-rank">#</span>
        <span className="rh-name">종목</span>
        <span className="rh-price">현재가</span>
        <span className="rh-star" />
      </div>
      <div className="ranking-list">
        {data.map(item => {
          const { price, changePct } = getDisplayPrice(item)
          return (
            <div
              key={item.symbol}
              className={`ranking-item ${item.symbol === currentSymbol ? 'active' : ''}`}
              onClick={() => setSymbol(item.symbol, item.name)}
            >
              <span className="r-rank">{item.rank}</span>
              <div className="r-info">
                <div className="r-name-row">
                  <span className="r-name">{item.name}</span>
                  {item.value_label && <span className="r-value-label">{item.value_label}</span>}
                </div>
                <span className="r-code">{item.symbol}</span>
              </div>
              <div className="r-price-col">
                {price != null
                  ? <span className="r-price">{fmtPrice(price)}</span>
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
