import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/stock'

interface Props { symbol: string }

const MA_PERIODS = [5, 20, 60, 120, 240]

export function Indicators({ symbol }: Props) {
  const { data } = useQuery({
    queryKey: ['indicators', symbol],
    queryFn: () => api.indicators(symbol),
    staleTime: 5 * 60 * 1000,
    enabled: !!symbol,
  })

  if (!data) return null

  const rsiColor = data.rsi == null ? '#6b7280'
    : data.rsi >= 70 ? '#ef4444'
    : data.rsi <= 30 ? '#3b82f6'
    : '#d1d5db'

  const volColor = (data.vol_ratio ?? 0) >= 500 ? '#ef4444'
    : (data.vol_ratio ?? 0) >= 200 ? '#f59e0b'
    : '#9ca3af'

  const maLabel = data.alignment ?? '—'

  // pct 오름차순 = MA 값 내림차순 (높은 MA가 앞)
  const sorted = MA_PERIODS
    .filter(p => data.all_mas[String(p)] != null)
    .map(p => ({ period: p, ...data.all_mas[String(p)] }))
    .sort((a, b) => a.pct - b.pct)

  // 인접 MA: pct < 0 중 최대(바로 위), pct > 0 중 최소(바로 아래)
  const aboveAdj = [...sorted].filter(m => m.pct < 0).at(-1)  // 현재가 바로 위 MA
  const belowAdj = sorted.find(m => m.pct > 0)                // 현재가 바로 아래 MA

  // "현" 삽입 위치: pct가 음수→양수 전환 지점
  let currentInserted = false
  const chain: { type: 'ma' | 'current'; period?: number; pct?: number; slope?: string; isAdj?: boolean }[] = []
  for (const ma of sorted) {
    if (!currentInserted && ma.pct > 0) {
      chain.push({ type: 'current' })
      currentInserted = true
    }
    chain.push({ type: 'ma', period: ma.period, pct: ma.pct, slope: ma.slope,
      isAdj: ma === aboveAdj || ma === belowAdj })
  }
  if (!currentInserted) chain.push({ type: 'current' })

  return (
    <div className="indicators">
      <div className="ind-row">
        <span className="ind-key">거래량</span>
        <span className="ind-val" style={{ color: volColor }}>20평 {data.vol_ratio}%</span>
      </div>
      <div className="ind-row">
        <span className="ind-key">RSI</span>
        <span className="ind-val" style={{ color: rsiColor }}>{data.rsi ?? '—'}</span>
      </div>
      <div className="ind-row">
        <span className="ind-key">이평</span>
        {(maLabel === '정' || maLabel === '역') && <span className="ind-val ind-align">{maLabel}</span>}
        <span className="ind-chain">
          {chain.map((item, i) => (
            <span key={i}>
              {i > 0 && <span className="ind-sep"> &gt; </span>}
              {item.type === 'current'
                ? <span className="ind-current">현</span>
                : (
                  <span className={item.pct! < 0 ? 'ind-ma-above' : 'ind-ma-below'}>
                    {item.period}
                    {item.isAdj && (
                      <span className="ind-ma-pct">
                        ({item.pct! < 0 ? '+' : ''}{Math.abs(item.pct!).toFixed(1)}%)
                      </span>
                    )}
                  </span>
                )
              }
            </span>
          ))}
        </span>
      </div>
    </div>
  )
}
