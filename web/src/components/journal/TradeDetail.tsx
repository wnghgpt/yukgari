import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store'
import { api } from '../../api/stock'
import type { JournalTrade } from '../../types'
import './TradeDetail.css'

const PATTERNS = ['손잡이컵', '손잡이컵 (놓침)', '역추세', '우량주', '횡보돌파', '횡보돌파 (놓침)']
const RESULTS  = ['보유', '감시', '수익', '손절']

const RESULT_COLOR: Record<string, string> = {
  보유: '#3b82f6', 감시: '#6b7280', 수익: '#2ecc71', 손절: '#ef4444',
}

const NUMERIC_COLS = new Set([
  'channel_top', 'channel_bottom',
  'entry1_price', 'entry2_price', 'entry3_price', 'entry4_price',
  'entry1_weight', 'entry2_weight', 'entry3_weight', 'entry4_weight',
  'stop_loss', 'target_price',
  'exit1_price', 'exit1_qty', 'exit2_price', 'exit2_qty',
  'rebound_price',
])

const isOverseas = (ticker: string) => /^[A-Z]{1,5}$/.test(ticker)

const parseVal = (col: string, v: string): unknown =>
  NUMERIC_COLS.has(col) ? (v === '' ? null : parseFloat(v) || null) : (v || null)

const shortDate = (d?: string | null) =>
  d ? d.replace(/^20(\d{2})-(\d{2})-(\d{2})$/, '$1.$2.$3') : '—'

function fmtP(v: number | null | undefined, ticker: string): string {
  if (!v) return '—'
  if (isOverseas(ticker)) return `$${v.toFixed(2)}`
  return (Math.round(v / 10) * 10).toLocaleString()
}

function calcAvgBuy(t: JournalTrade): number | null {
  const buys = (t.executions ?? []).filter(e => e.type === 'buy')
  if (buys.length) {
    const cost = buys.reduce((s, e) => s + e.price * e.qty, 0)
    const qty  = buys.reduce((s, e) => s + e.qty, 0)
    return qty > 0 ? cost / qty : null
  }
  // fallback: 계획 평단
  let cost = 0, qty = 0
  for (let i = 1; i <= 4; i++) {
    const p = t[`entry${i}_price` as keyof JournalTrade] as number | undefined
    const q = t[`entry${i}_weight` as keyof JournalTrade] as number | undefined
    if (p && q) { cost += p * q; qty += q }
  }
  return qty > 0 ? cost / qty : null
}

function calcProfitRate(t: JournalTrade, avg: number | null): number | null {
  const sells = (t.executions ?? []).filter(e => e.type === 'sell')
  if (sells.length) {
    const cost = sells.reduce((s, e) => s + e.price * e.qty, 0)
    const qty  = sells.reduce((s, e) => s + e.qty, 0)
    const avgSell = qty > 0 ? cost / qty : 0
    return avg ? (avgSell / avg - 1) * 100 : null
  }
  // fallback: exit 필드
  let cost = 0, qty = 0
  for (let i = 1; i <= 2; i++) {
    const p = t[`exit${i}_price` as keyof JournalTrade] as number | undefined
    const q = t[`exit${i}_qty` as keyof JournalTrade] as number | undefined
    if (p && q) { cost += p * q; qty += q }
  }
  if (!avg || !qty) return null
  return ((cost / qty) / avg - 1) * 100
}

// ── 인셀 편집 셀 ─────────────────────────────────────────────────

interface EditCell { col: string; value: string }

interface CellProps {
  col: string
  raw: unknown
  display: React.ReactNode
  editCell: EditCell | null
  setEditCell: (c: EditCell | null) => void
  onCommit: (col: string, value: string) => void
  inputType?: 'text' | 'number' | 'date'
  opts?: string[]
}

function Cell({ col, raw, display, editCell, setEditCell, onCommit, inputType = 'text', opts }: CellProps) {
  const editing = editCell?.col === col
  const commit = () => {
    if (editCell) onCommit(editCell.col, editCell.value)
    setEditCell(null)
  }
  if (editing) {
    if (opts) return (
      <select autoFocus className="td-input td-select"
        value={editCell!.value}
        onChange={e => setEditCell({ ...editCell!, value: e.target.value })}
        onBlur={commit}>
        <option value="">—</option>
        {opts.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    )
    return (
      <input autoFocus type={inputType} className="td-input"
        value={editCell!.value}
        onChange={e => setEditCell({ ...editCell!, value: e.target.value })}
        onBlur={commit}
        onKeyDown={e => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') setEditCell(null) }}
      />
    )
  }
  return (
    <span className="td-val" onClick={() => setEditCell({ col, value: raw != null ? String(raw) : '' })}>
      {display ?? <span className="td-na">—</span>}
    </span>
  )
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────

export function TradeDetail() {
  const { userId, selectedTradeId, setSelectedTradeId } = useAppStore()
  const queryClient = useQueryClient()
  const [editCell, setEditCell] = useState<EditCell | null>(null)

  const { data: trades = [] } = useQuery({
    queryKey: ['journal', userId],
    queryFn: () => api.journal(userId!),
    enabled: !!userId,
  })

  const trade = trades.find(t => t.id === selectedTradeId) ?? null

  const updateMutation = useMutation({
    mutationFn: ({ col, value }: EditCell) =>
      api.updateJournal(trade!.id, { [col]: parseVal(col, value) }, userId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['journal', userId] }),
  })

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteJournal(trade!.id, userId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal', userId] })
      setSelectedTradeId(null)
    },
  })

  const onCommit = (col: string, value: string) => updateMutation.mutate({ col, value })

  const cell = (col: string, raw: unknown, display: React.ReactNode, inputType: 'text' | 'number' | 'date' = 'text', opts?: string[]) => (
    <Cell col={col} raw={raw} display={display} editCell={editCell} setEditCell={setEditCell} onCommit={onCommit} inputType={inputType} opts={opts} />
  )

  if (!trade) {
    return <div className="td-empty">MY 탭에서 항목을 선택하세요</div>
  }

  const avg = calcAvgBuy(trade)
  const rate = calcProfitRate(trade, avg)
  const t = trade

  const filledQty = (tier: number) =>
    (t.executions ?? []).filter(e => e.tier === tier && e.type === 'buy').reduce((s, e) => s + e.qty, 0)

  const tierAvg = (tier: number) => {
    const fills = (t.executions ?? []).filter(e => e.tier === tier && e.type === 'buy')
    if (!fills.length) return null
    const cost = fills.reduce((s, e) => s + e.price * e.qty, 0)
    const qty  = fills.reduce((s, e) => s + e.qty, 0)
    return qty > 0 ? cost / qty : null
  }

  return (
    <div className="trade-detail">
      {/* 헤더 */}
      <div className="td-header">
        <div className="td-header-left">
          <span className="td-name">{t.name ?? t.ticker}</span>
          <span className="td-ticker-sub">{t.ticker}</span>
        </div>
        <div className="td-header-right">
          <span className="td-result-badge" style={{ color: RESULT_COLOR[t.result] ?? '#9ca3af' }}>
            {cell('result', t.result, t.result, 'text', RESULTS)}
          </span>
          <button className="td-delete-btn" onClick={() => window.confirm('삭제하시겠습니까?') && deleteMutation.mutate()}>
            삭제
          </button>
        </div>
      </div>

      {/* 기본 정보 */}
      <div className="td-section">
        <div className="td-row">
          <span className="td-label">패턴</span>
          <span className="td-field">{cell('pattern', t.pattern, t.pattern, 'text', PATTERNS)}</span>
        </div>
        <div className="td-row">
          <span className="td-label">진입일</span>
          <span className="td-field">{cell('date', t.date, shortDate(t.date), 'date')}</span>
          <span className="td-label">청산일</span>
          <span className="td-field">{cell('exit_date', t.exit_date, shortDate(t.exit_date), 'date')}</span>
        </div>
        <div className="td-row">
          <span className="td-label">채널상단</span>
          <span className="td-field">{cell('channel_top', t.channel_top, fmtP(t.channel_top, t.ticker), 'number')}</span>
          <span className="td-label">채널하단</span>
          <span className="td-field">{cell('channel_bottom', t.channel_bottom, fmtP(t.channel_bottom, t.ticker), 'number')}</span>
        </div>
      </div>

      {/* 매수 계획 */}
      <div className="td-section">
        <div className="td-section-title">매수 계획</div>
        {[1, 2, 3, 4].map(i => {
          const price  = t[`entry${i}_price`  as keyof JournalTrade] as number | undefined
          const weight = t[`entry${i}_weight` as keyof JournalTrade] as number | undefined
          if (!price && !weight) return null
          const filled = filledQty(i)
          const actual = tierAvg(i)
          return (
            <div key={i} className="td-row td-tier-row">
              <span className="td-label">{i}차</span>
              <span className="td-field">
                {cell(`entry${i}_price`, price, fmtP(price, t.ticker), 'number')}
              </span>
              <span className="td-field td-weight">
                {cell(`entry${i}_weight`, weight, weight ? `${weight}주` : null, 'number')}
              </span>
              <span className={`td-fill ${filled > 0 ? 'filled' : 'empty'}`}>
                {actual ? `체결 ${fmtP(actual, t.ticker)}` : filled > 0 ? `${filled}주` : '미체결'}
              </span>
            </div>
          )
        })}
      </div>

      {/* 손절/목표 */}
      <div className="td-section">
        <div className="td-row">
          <span className="td-label">손절가</span>
          <span className="td-field td-sl-val">
            {cell('stop_loss', t.stop_loss, fmtP(t.stop_loss, t.ticker), 'number')}
          </span>
          <span className="td-label">목표가</span>
          <span className="td-field td-tp-val">
            {cell('target_price', t.target_price, fmtP(t.target_price, t.ticker), 'number')}
          </span>
        </div>
        {avg != null && (
          <div className="td-row">
            <span className="td-label">평단</span>
            <span className="td-field td-avg">{fmtP(avg, t.ticker)}</span>
            {rate != null && (
              <>
                <span className="td-label">수익률</span>
                <span className="td-field" style={{ color: rate >= 0 ? '#2ecc71' : '#ef4444' }}>
                  {rate >= 0 ? '+' : ''}{rate.toFixed(2)}%
                </span>
              </>
            )}
          </div>
        )}
      </div>

      {/* 체결 내역 */}
      {(t.executions ?? []).length > 0 && (
        <div className="td-section">
          <div className="td-section-title">체결 내역</div>
          <div className="td-execs">
            {t.executions!.map((e, idx) => (
              <div key={idx} className={`td-exec-row ${e.type}`}>
                <span className="td-exec-date">{shortDate(e.date)}</span>
                <span className="td-exec-tier">{e.type === 'buy' ? `${e.tier}차` : '매도'}</span>
                <span className="td-exec-price">{fmtP(e.price, t.ticker)}</span>
                <span className="td-exec-qty">{e.qty}주</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 메모 */}
      <div className="td-section">
        <div className="td-row">
          <span className="td-label">메모</span>
          <span className="td-field td-memo-field">
            {cell('memo', t.memo, t.memo || null, 'text')}
          </span>
        </div>
      </div>
    </div>
  )
}
