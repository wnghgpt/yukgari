import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store'
import { StrategyTab, type JournalPayload } from './StrategyTab'
import { JournalAddModal } from '../journal/JournalAddModal'
import { JournalDirectForm } from '../journal/JournalDirectForm'
import { api } from '../../api/stock'
import './Calculator.css'

const TABS = [
  { id: 'cup',      label: '손잡이컵' },
  { id: 'reversal', label: '역추세'   },
  { id: 'blue',     label: '우량주'   },
  { id: 'sideways', label: '횡보돌파' },
]

const TAB_PATTERN: Record<string, (missed: boolean) => string> = {
  cup:      m => m ? '손잡이컵 (놓침)' : '손잡이컵',
  reversal: _ => '역추세',
  blue:     _ => '우량주',
  sideways: m => m ? '횡보돌파 (놓침)' : '횡보돌파',
}

export function Calculator() {
  const [activeTab, setActiveTab] = useState('cup')
  const { symbol, symbolName, totalAsset, riskPct, setTotalAsset, setRiskPct, livePrices } = useAppStore()
  const [modalOpen, setModalOpen] = useState(false)
  const [suggestedPattern, setSuggestedPattern] = useState('손잡이컵')
  const pendingPayload = useRef<JournalPayload | null>(null)
  const [showDirectForm, setShowDirectForm] = useState(false)
  const [directPayload, setDirectPayload] = useState<JournalPayload | null>(null)
  const queryClient = useQueryClient()

  const isOverseas = !/^\d+$/.test(symbol)
  const assetStep  = isOverseas ? 100 : 1_000_000

  // websocket 없을 때 API로 폴백
  const { data: priceData } = useQuery({
    queryKey: ['price', symbol],
    queryFn: () => api.price(symbol),
    staleTime: 60_000,
    enabled: !!symbol && !livePrices[symbol],
  })
  const currentPrice = livePrices[symbol] ?? priceData?.price ?? 0

  const allowedLoss = totalAsset * riskPct / 100
  const fmtLoss = isOverseas
    ? `$${allowedLoss.toFixed(0)}`
    : `${(allowedLoss / 10000).toFixed(1)}만원`

  const addMutation = useMutation({
    mutationFn: api.addJournal,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['journal'] }),
  })

  const handleJournalAdd = (payload: JournalPayload) => {
    pendingPayload.current = payload
    setSuggestedPattern(TAB_PATTERN[activeTab]?.(payload.missed) ?? '손잡이컵')
    setModalOpen(true)
  }

  const handleDirectEntry = (payload: JournalPayload | null) => {
    setDirectPayload(payload)
    setSuggestedPattern(TAB_PATTERN[activeTab]?.(payload?.missed ?? false) ?? '손잡이컵')
    setShowDirectForm(true)
  }

  const handleModalConfirm = (pattern: string) => {
    const p = pendingPayload.current
    if (!p) return
    const today = new Date().toISOString().split('T')[0]
    const body: Record<string, unknown> = {
      ticker: symbol,
      name: symbolName,
      pattern,
      date: today,
      stages: p.entryPrices.length,
      channel_top: p.resistPrice,
      channel_bottom: p.supportPrice || null,
      stop_loss: p.stopLoss,
      target_price: p.targetPrice,
      result: '감시',
    }
    p.entryPrices.forEach((price, i) => { body[`entry${i + 1}_price`] = price })
    p.quantities.forEach((qty, i)   => { body[`entry${i + 1}_weight`] = Math.floor(qty) })
    addMutation.mutate(body)
    setModalOpen(false)
  }

  const commonProps = {
    symbol, currentPrice, isOverseas, allowedLoss,
    onJournalAdd: handleJournalAdd,
    onDirectEntry: handleDirectEntry,
  }

  return (
    <div className="calculator">
      <JournalAddModal
        open={modalOpen}
        defaultPattern={suggestedPattern}
        onConfirm={handleModalConfirm}
        onCancel={() => setModalOpen(false)}
      />
      {/* 공통 헤더 */}
      <div className="calc-header">
        <div className="calc-header-row">
          <div className="calc-field">
            <label className="calc-field-label">총액 ({isOverseas ? '$' : '원'})</label>
            <input
              type="number" className="calc-field-input"
              value={totalAsset || ''} step={assetStep}
              placeholder={isOverseas ? '10000' : '50000000'}
              onChange={e => setTotalAsset(e.target.value === '' ? 0 : +e.target.value)}
            />
          </div>
          <div className="calc-field calc-field-sm">
            <label className="calc-field-label">비중%</label>
            <input
              type="number" className="calc-field-input"
              value={riskPct || ''} step={0.05} min={0}
              placeholder="0.4"
              onChange={e => setRiskPct(e.target.value === '' ? 0 : +e.target.value)}
            />
          </div>
          <div className="calc-loss">
            허용손실 <span className="loss-val">{fmtLoss}</span>
          </div>
        </div>
      </div>

      <hr className="calc-divider" />

      {/* 직접 입력 폼 */}
      {showDirectForm && (
        <JournalDirectForm
          ticker={symbol}
          defaultPattern={suggestedPattern}
          payload={directPayload}
          isOverseas={isOverseas}
          onSave={() => setShowDirectForm(false)}
          onCancel={() => setShowDirectForm(false)}
        />
      )}

      {/* 전략 탭 */}
      {!showDirectForm && (
        <>
          <div className="calc-tabs">
            {TABS.map(t => (
              <button key={t.id}
                className={`calc-tab ${activeTab === t.id ? 'active' : ''}`}
                onClick={() => setActiveTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="calc-tab-content">
            {activeTab === 'cup' && (
              <StrategyTab {...commonProps}
                defaultSlPct={4.0} missedSlPct={5.0} mode="breakout" rrMultiple={4} />
            )}
            {activeTab === 'reversal' && (
              <StrategyTab {...commonProps}
                defaultSlPct={7.0} missedSlPct={8.0} mode="zone" rrMultiple={4} />
            )}
            {activeTab === 'blue' && (
              <StrategyTab {...commonProps}
                defaultSlPct={10.0} missedSlPct={10.0} mode="forceZone" rrMultiple={3} />
            )}
            {activeTab === 'sideways' && (
              <StrategyTab {...commonProps}
                defaultSlPct={7.0} missedSlPct={7.0} mode="zone" rrMultiple={5} />
            )}
          </div>
        </>
      )}
    </div>
  )
}
