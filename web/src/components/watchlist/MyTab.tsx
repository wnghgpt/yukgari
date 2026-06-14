import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '../../store'
import { usePriceSocket } from '../../hooks/usePriceSocket'
import { api } from '../../api/stock'
import type { JournalTrade } from '../../types'

type MySubTab = '감시' | '보유' | '수익' | '손절'
const SUBTABS: MySubTab[] = ['감시', '보유', '수익', '손절']

const isOverseas = (sym: string) => !/^\d+$/.test(sym)

function fmtPrice(sym: string, price: number): string {
  return isOverseas(sym) ? `$${price.toFixed(2)}` : price.toLocaleString()
}

function fmtLevel(sym: string, price: number): string {
  return isOverseas(sym) ? `$${price.toFixed(0)}` : Math.round(price).toLocaleString()
}

function fmtPct(val: number): string {
  return `${val >= 0 ? '+' : ''}${val.toFixed(1)}%`
}

function daysSince(dateStr: string): number {
  return Math.max(0, Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000))
}

function daysBetween(from: string, to: string): number {
  return Math.max(0, Math.floor((new Date(to).getTime() - new Date(from).getTime()) / 86400000))
}

function avgBuyPrice(trade: JournalTrade): number | null {
  const buys = (trade.executions ?? []).filter(e => e.type === 'buy')
  if (!buys.length) return null
  const cost = buys.reduce((s, e) => s + e.price * e.qty, 0)
  const qty = buys.reduce((s, e) => s + e.qty, 0)
  return qty > 0 ? cost / qty : null
}

function avgSellPrice(trade: JournalTrade): number | null {
  const sells = (trade.executions ?? []).filter(e => e.type === 'sell')
  if (!sells.length) return null
  const cost = sells.reduce((s, e) => s + e.price * e.qty, 0)
  const qty = sells.reduce((s, e) => s + e.qty, 0)
  return qty > 0 ? cost / qty : null
}

function getNextTier(trade: JournalTrade): { tier: number; price: number } | null {
  const execs = trade.executions ?? []
  for (let t = 1; t <= 4; t++) {
    const planned = trade[`entry${t}_weight` as keyof JournalTrade] as number | undefined
    if (!planned) continue
    const filled = execs.filter(e => e.tier === t && e.type === 'buy').reduce((s, e) => s + e.qty, 0)
    if (filled < planned) {
      const price = trade[`entry${t}_price` as keyof JournalTrade] as number | undefined
      return price ? { tier: t, price } : null
    }
  }
  return null
}

function firstBuyDate(trade: JournalTrade): string {
  const buys = (trade.executions ?? []).filter(e => e.type === 'buy')
  if (!buys.length) return trade.date
  return buys.reduce((min, e) => (e.date < min ? e.date : min), buys[0].date)
}

// ── Card components ──────────────────────────────────────────────

interface CardProps {
  trade: JournalTrade
  subTab: MySubTab
  currentPrice?: number
  prevClose?: number
  isActive: boolean
  onClick: () => void
}

function TradeCard({ trade, subTab, currentPrice, prevClose, isActive, onClick }: CardProps) {
  const changePct =
    currentPrice != null && prevClose != null && prevClose > 0
      ? ((currentPrice - prevClose) / prevClose) * 100
      : null

  if (subTab === '감시') {
    const d = daysSince(trade.date)
    const entry1Pct =
      currentPrice != null && trade.entry1_price
        ? ((trade.entry1_price / currentPrice) - 1) * 100
        : null

    return (
      <div className={`my-card ${isActive ? 'active' : ''}`} onClick={onClick}>
        <div className="my-card-body">
          <div className="my-card-left">
            <div className="my-card-top">
              <span className="my-card-name">{trade.name ?? trade.ticker}</span>
              <div className="my-card-meta">
                <span className="my-card-pattern">{trade.pattern}</span>
                <span className="my-card-days">D+{d}</span>
              </div>
            </div>
            <div className="my-card-price-wrap">
              {currentPrice != null
                ? <><span className="my-card-price">{fmtPrice(trade.ticker, currentPrice)}</span>
                    {changePct != null && (
                      <span className={`my-card-change ${changePct >= 0 ? 'up' : 'down'}`}>
                        {fmtPct(changePct)}
                      </span>
                    )}</>
                : <span className="my-card-price">—</span>}
            </div>
            {(trade.channel_top || trade.channel_bottom) && (
              <div className="my-card-levels">
                {trade.channel_top && <span>저 {fmtLevel(trade.ticker, trade.channel_top)}</span>}
                {trade.channel_bottom && <span>지 {fmtLevel(trade.ticker, trade.channel_bottom)}</span>}
              </div>
            )}
          </div>
          {entry1Pct != null && (
            <span className={`my-card-1ch ${entry1Pct >= 0 ? 'up' : 'down'}`}>
              {fmtPct(entry1Pct)}
            </span>
          )}
        </div>
      </div>
    )
  }

  if (subTab === '보유') {
    const d = daysSince(firstBuyDate(trade))
    const avg = avgBuyPrice(trade)
    const returnPct = avg && currentPrice != null ? ((currentPrice / avg) - 1) * 100 : null
    const next = getNextTier(trade)
    const nextPct = next && currentPrice != null ? ((next.price / currentPrice) - 1) * 100 : null
    const slPct =
      trade.stop_loss && currentPrice != null
        ? ((trade.stop_loss / currentPrice) - 1) * 100
        : null

    return (
      <div className={`my-card ${isActive ? 'active' : ''}`} onClick={onClick}>
        <div className="my-card-top">
          <span className="my-card-name">{trade.name ?? trade.ticker}</span>
          <div className="my-card-meta">
            <span className="my-card-pattern">{trade.pattern}</span>
            <span className="my-card-days">D+{d}</span>
          </div>
        </div>
        <div className="my-card-mid">
          <div className="my-card-price-wrap">
            {currentPrice != null
              ? <><span className="my-card-price">{fmtPrice(trade.ticker, currentPrice)}</span>
                  {changePct != null && (
                    <span className={`my-card-change ${changePct >= 0 ? 'up' : 'down'}`}>
                      {fmtPct(changePct)}
                    </span>
                  )}</>
              : <span className="my-card-price">—</span>}
          </div>
          {returnPct != null && (
            <span className={`my-card-right-val ${returnPct >= 0 ? 'up' : 'down'}`}>
              {fmtPct(returnPct)}
            </span>
          )}
        </div>
        <div className="my-card-bot">
          <span className="my-card-bot-item">
            {next ? `${next.tier}차 ` : '다음 차수 없음'}
            {nextPct != null && (
              <span className={`my-card-bot-val ${nextPct >= 0 ? 'up' : 'down'}`}>
                {fmtPct(nextPct)}
              </span>
            )}
          </span>
          <span className="my-card-bot-item">
            손절{' '}
            {slPct != null && (
              <span className="my-card-bot-val down">{fmtPct(slPct)}</span>
            )}
          </span>
        </div>
        {(trade.channel_top || trade.channel_bottom) && (
          <div className="my-card-levels">
            {trade.channel_top && <span>저 {fmtLevel(trade.ticker, trade.channel_top)}</span>}
            {trade.channel_bottom && <span>지 {fmtLevel(trade.ticker, trade.channel_bottom)}</span>}
          </div>
        )}
      </div>
    )
  }

  // 수익 / 손절
  const buyAvg = avgBuyPrice(trade)
  const sellAvg = avgSellPrice(trade)
  const returnPct = buyAvg && sellAvg ? ((sellAvg / buyAvg) - 1) * 100 : null
  const holdDays =
    trade.exit_date ? daysBetween(trade.date, trade.exit_date) : null

  return (
    <div className={`my-card ${isActive ? 'active' : ''}`} onClick={onClick}>
      <div className="my-card-top">
        <span className="my-card-name">{trade.name ?? trade.ticker}</span>
        <span className="my-card-pattern">{trade.pattern}</span>
      </div>
      <div className="my-card-mid">
        {returnPct != null && (
          <span className={`my-card-right-val ${returnPct >= 0 ? 'up' : 'down'}`}>
            {fmtPct(returnPct)}
          </span>
        )}
        {holdDays != null && (
          <span className="my-card-days">{holdDays}일 보유</span>
        )}
      </div>
    </div>
  )
}

// ── Main MyTab ────────────────────────────────────────────────────

export function MyTab() {
  const {
    userId, symbol: currentSymbol,
    setSymbol, setRightTab, setSelectedTradeId,
    mySubTab: subTab, setMySubTab: setSubTab,
    livePrices, setLivePrice,
    prevCloses, setPrevClose,
  } = useAppStore()

  const { data: trades = [] } = useQuery({
    queryKey: ['journal', userId],
    queryFn: () => api.journal(userId!),
    enabled: !!userId,
    staleTime: 30_000,
  })

  const { subscribe } = usePriceSocket((sym, price) => setLivePrice(sym, price))

  const activeTickers = trades
    .filter(t => t.result === '감시' || t.result === '보유')
    .map(t => t.ticker)

  // 감시+보유 종목 구독 및 초기 가격 로드
  useEffect(() => {
    activeTickers.forEach(sym => {
      subscribe(sym)
      api.price(sym).then(r => {
        if (r.prev_close != null) setPrevClose(sym, r.prev_close)
        if (r.price != null) setLivePrice(sym, r.price)
      }).catch(() => {})
    })
  }, [activeTickers.join(',')]) // eslint-disable-line react-hooks/exhaustive-deps

  const filtered = trades.filter(t => t.result === subTab)

  const sorted = [...filtered].sort((a, b) => {
    if (subTab === '감시') {
      const pa = livePrices[a.ticker], pb = livePrices[b.ticker]
      if (!pa || !a.entry1_price) return 1
      if (!pb || !b.entry1_price) return -1
      return Math.abs(a.entry1_price - pa) - Math.abs(b.entry1_price - pb)
    }
    if (subTab === '보유') {
      const pa = livePrices[a.ticker], pb = livePrices[b.ticker]
      if (!pa || !a.stop_loss) return 1
      if (!pb || !b.stop_loss) return -1
      return (pa - a.stop_loss) / pa - (pb - b.stop_loss) / pb
    }
    return 0
  })

  const count = (tab: MySubTab) => trades.filter(t => t.result === tab).length

  return (
    <div className="my-tab">
      <div className="my-subtabs">
        {SUBTABS.map(t => (
          <button
            key={t}
            className={`my-subtab ${subTab === t ? 'active' : ''}`}
            onClick={() => setSubTab(t)}
          >
            {t}{count(t) > 0 && <span className="my-subtab-cnt"> {count(t)}</span>}
          </button>
        ))}
      </div>

      <div className="my-list">
        {sorted.length === 0 && <div className="my-empty">항목 없음</div>}
        {sorted.map(trade => (
          <TradeCard
            key={trade.id}
            trade={trade}
            subTab={subTab}
            currentPrice={livePrices[trade.ticker]}
            prevClose={prevCloses[trade.ticker]}
            isActive={trade.ticker === currentSymbol}
            onClick={() => { setSymbol(trade.ticker, trade.name ?? trade.ticker); setSelectedTradeId(trade.id); setRightTab('journal') }}
          />
        ))}
      </div>
    </div>
  )
}
