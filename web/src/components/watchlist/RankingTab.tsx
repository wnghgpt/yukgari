import { useAppStore } from '../../store'
import { useWatchlist } from '../../hooks/useWatchlist'
import type { RankingItem } from '../../types'

interface Props {
  data: RankingItem[]
  loading: boolean
  valueHeader: string
}

export function RankingTab({ data, loading, valueHeader }: Props) {
  const { setSymbol, symbol: currentSymbol } = useAppStore()
  const { isInWatchlist, toggle } = useWatchlist()

  if (loading && data.length === 0) {
    return <div className="wl-loading">불러오는 중...</div>
  }

  return (
    <div className="ranking-tab">
      <div className="ranking-header">
        <span className="rh-rank">#</span>
        <span className="rh-name">종목</span>
        <span className="rh-value">{valueHeader}</span>
        <span className="rh-star" />
      </div>
      <div className="ranking-list">
        {data.map(item => (
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
            <span className="r-value">{item.value_label}</span>
            <button
              className={`wl-star-btn ${isInWatchlist(item.symbol) ? 'starred' : ''}`}
              onClick={e => { e.stopPropagation(); toggle(item.symbol, item.name) }}
            >
              {isInWatchlist(item.symbol) ? '⭐' : '☆'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
