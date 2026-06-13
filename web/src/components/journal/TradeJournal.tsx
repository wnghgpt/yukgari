import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAppStore } from '../../store'
import { api } from '../../api/stock'
import type { JournalTrade } from '../../types'
import './TradeJournal.css'

// ── 상수 ─────────────────────────────────────────────────────

const isOverseas = (ticker: string) => /^[A-Z]{1,5}$/.test(ticker)

const PATTERNS = ['손잡이컵', '손잡이컵 (놓침)', '역추세', '우량주', '횡보돌파', '횡보돌파 (놓침)']
const RESULTS  = ['보유', '감시', '수익', '손절']

const PATTERN_SHORT: Record<string, string> = {
  '손잡이컵': '컵', '손잡이컵 (놓침)': '컵↑',
  '역추세': '역추세', '우량주': '우량주',
  '횡보돌파': '횡보', '횡보돌파 (놓침)': '횡보↑',
}

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

// ── 헬퍼 ─────────────────────────────────────────────────────

const shortDate = (d?: string | null) =>
  d ? d.replace(/^20(\d{2})-(\d{2})-(\d{2})$/, '$1.$2.$3') : ''

const parseVal = (col: string, v: string): unknown =>
  NUMERIC_COLS.has(col) ? (v === '' ? null : parseFloat(v) || null) : (v || null)

// ── 프론트 계산 ───────────────────────────────────────────────

function calcAvgPrice(t: JournalTrade): number | null {
  let cost = 0, qty = 0
  for (let i = 1; i <= 4; i++) {
    const p = t[`entry${i}_price` as keyof JournalTrade] as number | undefined
    const q = t[`entry${i}_weight` as keyof JournalTrade] as number | undefined
    if (p && q && p > 0 && q > 0) { cost += p * q; qty += q }
  }
  return qty > 0 ? cost / qty : null
}

function calcExitAvg(t: JournalTrade) {
  let cost = 0, qty = 0
  for (let i = 1; i <= 2; i++) {
    const p = t[`exit${i}_price` as keyof JournalTrade] as number | undefined
    const q = t[`exit${i}_qty` as keyof JournalTrade] as number | undefined
    if (p && q && p > 0 && q > 0) { cost += p * q; qty += q }
  }
  return qty > 0 ? { price: cost / qty, qty } : null
}

function calcProfitRate(t: JournalTrade, avg: number | null) {
  const exit = calcExitAvg(t)
  if (!avg || !exit) return null
  return (exit.price - avg) / avg * 100
}

function calcProfitAmount(t: JournalTrade, avg: number | null) {
  const exit = calcExitAvg(t)
  if (!avg || !exit) return null
  return (exit.price - avg) * exit.qty
}

function holdingDays(t: JournalTrade) {
  if (!t.date) return null
  const end = t.exit_date ? new Date(t.exit_date) : new Date()
  return Math.floor((end.getTime() - new Date(t.date).getTime()) / 86400000)
}

// ── 정렬 ─────────────────────────────────────────────────────

const RESULT_ORDER: Record<string, number> = { 보유: 0, 감시: 1, 수익: 2, 손절: 3 }

const sortTrades = (trades: JournalTrade[]) =>
  [...trades].sort((a, b) => {
    const ro = (RESULT_ORDER[a.result] ?? 4) - (RESULT_ORDER[b.result] ?? 4)
    return ro !== 0 ? ro : (b.date ?? '').localeCompare(a.date ?? '')
  })

// ── 요약 바 ───────────────────────────────────────────────────

function SummaryBar({ trades }: { trades: JournalTrade[] }) {
  const s = useMemo(() => {
    const closed = trades.filter(t => t.result === '수익' || t.result === '손절')
    const wins   = trades.filter(t => t.result === '수익')
    const losses = trades.filter(t => t.result === '손절')
    const winRate = closed.length > 0 ? wins.length / closed.length * 100 : 0
    const wr = (arr: JournalTrade[]) =>
      arr.map(t => calcProfitRate(t, calcAvgPrice(t))).filter((v): v is number => v != null)
    const avg = (ns: number[]) => ns.length ? ns.reduce((a, b) => a + b, 0) / ns.length : 0
    const avgWin = avg(wr(wins)); const avgLoss = avg(wr(losses))
    const rr = avgLoss !== 0 ? Math.abs(avgWin / avgLoss) : 0
    return {
      nHold: trades.filter(t => t.result === '보유').length,
      nWatch: trades.filter(t => t.result === '감시').length,
      nClosed: closed.length, winRate, rr,
    }
  }, [trades])

  return (
    <div className="journal-summary">
      <span className="summary-item">보유 <b>{s.nHold}</b></span>
      <span className="summary-item">감시 <b>{s.nWatch}</b></span>
      <span className="summary-item">거래 <b>{s.nClosed}건</b></span>
      <span className="summary-item">승률 <b style={{ color: s.winRate >= 50 ? '#2ecc71' : '#ef4444' }}>{s.winRate.toFixed(0)}%</b></span>
      <span className="summary-item">손익비 <b style={{ color: s.rr >= 1 ? '#2ecc71' : '#ef4444' }}>{s.rr.toFixed(1)}x</b></span>
    </div>
  )
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────

interface EditCell { id: string; col: string; value: string }

export function TradeJournal() {
  const { userId } = useAppStore()
  const queryClient = useQueryClient()
  const [editCell, setEditCell] = useState<EditCell | null>(null)

  const { data: trades = [], isLoading } = useQuery({
    queryKey: ['journal', userId],
    queryFn: () => api.journal(userId!),
    enabled: !!userId,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, col, value }: EditCell) =>
      api.updateJournal(id, { [col]: parseVal(col, value) }, userId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['journal', userId] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteJournal(id, userId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['journal', userId] }),
  })

  const sorted = useMemo(() => sortTrades(trades), [trades])

  // ── 인셀 편집 헬퍼 ──────────────────────────────────────────

  const startEdit = (id: string, col: string, raw: unknown) =>
    setEditCell({ id, col, value: raw != null ? String(raw) : '' })

  const commitEdit = () => {
    if (editCell) updateMutation.mutate(editCell)
    setEditCell(null)
  }

  const cancelEdit = () => setEditCell(null)

  // col 편집 셀 렌더: display 값 + 편집 input 전환
  const C = (
    id: string, col: string, raw: unknown,
    display: React.ReactNode,
    inputType: 'text' | 'number' | 'date' = 'text',
    opts?: string[],
  ) => {
    const editing = editCell?.id === id && editCell?.col === col
    if (editing) {
      if (opts) return (
        <select autoFocus className="cell-input cell-select"
          value={editCell!.value}
          onChange={e => setEditCell({ ...editCell!, value: e.target.value })}
          onBlur={commitEdit}>
          <option value="">-</option>
          {opts.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      )
      return (
        <input autoFocus type={inputType} className="cell-input"
          value={editCell!.value}
          onChange={e => setEditCell({ ...editCell!, value: e.target.value })}
          onBlur={commitEdit}
          onKeyDown={e => { if (e.key === 'Enter') commitEdit(); if (e.key === 'Escape') cancelEdit() }}
        />
      )
    }
    return <span className="cell-value" onClick={() => startEdit(id, col, raw)}>{display ?? <span className="td-na">-</span>}</span>
  }

  // ── 포맷 헬퍼 ───────────────────────────────────────────────

  const fmtP = (v: number | null | undefined, ticker: string) => {
    if (!v) return null
    if (isOverseas(ticker)) return `$${v.toFixed(2)}`
    return (Math.round(v / 10) * 10).toLocaleString()
  }

  const fmtRate = (v: number | null) => {
    if (v == null) return null
    const c = v >= 0 ? '#2ecc71' : '#ef4444'
    return <span style={{ color: c }}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</span>
  }

  const fmtAmount = (v: number | null, ticker: string) => {
    if (v == null) return null
    const c = v >= 0 ? '#2ecc71' : '#ef4444'
    const s = isOverseas(ticker) ? `$${Math.round(v).toLocaleString()}` : `${(v / 10000).toFixed(0)}만`
    return <span style={{ color: c }}>{s}</span>
  }

  if (isLoading) return <div className="journal-loading">로딩 중...</div>

  return (
    <div className="trade-journal">
      <div className="journal-header">
        <span className="journal-title">매매일지</span>
        <SummaryBar trades={trades} />
      </div>

      {sorted.length === 0 ? (
        <p className="journal-empty">일지가 없습니다. 계산기에서 일지에 추가를 눌러보세요.</p>
      ) : (
        <div className="journal-table-wrap">
          <table className="journal-table">
            <thead>
              <tr>
                <th>결과</th><th>진입일</th><th>청산일</th><th>보유</th>
                <th>종목</th><th>패턴</th>
                <th>저항</th><th>지지</th>
                <th colSpan={2}>1차가/주</th>
                <th colSpan={2}>2차가/주</th>
                <th colSpan={2}>3차가/주</th>
                <th colSpan={2}>4차가/주</th>
                <th>손절</th><th>평단</th><th>목표</th>
                <th colSpan={2}>청1가/주</th>
                <th colSpan={2}>청2가/주</th>
                <th>수익률</th><th>수익금</th><th>손절반등</th><th>메모</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(t => {
                const avg    = calcAvgPrice(t)
                const rate   = calcProfitRate(t, avg)
                const amount = calcProfitAmount(t, avg)
                const days   = holdingDays(t)
                return (
                  <tr key={t.id} className="journal-row">
                    {/* 결과 */}
                    <td onClick={() => startEdit(t.id, 'result', t.result)} style={{ cursor: 'pointer' }}>
                      {editCell?.id === t.id && editCell.col === 'result' ? (
                        <select autoFocus className="cell-input cell-select"
                          value={editCell.value}
                          onChange={e => setEditCell({ ...editCell, value: e.target.value })}
                          onBlur={commitEdit}>
                          {RESULTS.map(r => <option key={r}>{r}</option>)}
                        </select>
                      ) : (
                        <span className="result-badge" style={{ color: RESULT_COLOR[t.result] ?? '#9ca3af' }}>
                          {t.result}
                        </span>
                      )}
                    </td>

                    {/* 날짜 */}
                    <td>{C(t.id, 'date', t.date, shortDate(t.date), 'date')}</td>
                    <td>{C(t.id, 'exit_date', t.exit_date, shortDate(t.exit_date), 'date')}</td>
                    <td className="td-num td-ro">{days ?? <span className="td-na">-</span>}</td>

                    {/* 종목/패턴 */}
                    <td className="td-ticker">{C(t.id, 'ticker', t.ticker, t.ticker, 'text')}</td>
                    <td className="td-pattern">
                      {C(t.id, 'pattern', t.pattern, PATTERN_SHORT[t.pattern] ?? t.pattern, 'text', PATTERNS)}
                    </td>

                    {/* 가격 범위 */}
                    <td>{C(t.id, 'channel_top',    t.channel_top,    fmtP(t.channel_top,    t.ticker), 'number')}</td>
                    <td>{C(t.id, 'channel_bottom',  t.channel_bottom, fmtP(t.channel_bottom, t.ticker), 'number')}</td>

                    {/* 차수별 매수 */}
                    <td>{C(t.id, 'entry1_price',  t.entry1_price,  fmtP(t.entry1_price,  t.ticker), 'number')}</td>
                    <td className="td-num">{C(t.id, 'entry1_weight', t.entry1_weight, t.entry1_weight, 'number')}</td>
                    <td>{C(t.id, 'entry2_price',  t.entry2_price,  fmtP(t.entry2_price,  t.ticker), 'number')}</td>
                    <td className="td-num">{C(t.id, 'entry2_weight', t.entry2_weight, t.entry2_weight, 'number')}</td>
                    <td>{C(t.id, 'entry3_price',  t.entry3_price,  fmtP(t.entry3_price,  t.ticker), 'number')}</td>
                    <td className="td-num">{C(t.id, 'entry3_weight', t.entry3_weight, t.entry3_weight, 'number')}</td>
                    <td>{C(t.id, 'entry4_price',  t.entry4_price,  fmtP(t.entry4_price,  t.ticker), 'number')}</td>
                    <td className="td-num">{C(t.id, 'entry4_weight', t.entry4_weight, t.entry4_weight, 'number')}</td>

                    {/* 손절/평단/목표 */}
                    <td className="td-sl">{C(t.id, 'stop_loss',    t.stop_loss,    fmtP(t.stop_loss,    t.ticker), 'number')}</td>
                    <td className="td-ro">{fmtP(avg, t.ticker) ?? <span className="td-na">-</span>}</td>
                    <td className="td-target">{C(t.id, 'target_price', t.target_price, fmtP(t.target_price, t.ticker), 'number')}</td>

                    {/* 청산 */}
                    <td>{C(t.id, 'exit1_price', t.exit1_price, fmtP(t.exit1_price, t.ticker), 'number')}</td>
                    <td className="td-num">{C(t.id, 'exit1_qty', t.exit1_qty, t.exit1_qty, 'number')}</td>
                    <td>{C(t.id, 'exit2_price', t.exit2_price, fmtP(t.exit2_price, t.ticker), 'number')}</td>
                    <td className="td-num">{C(t.id, 'exit2_qty', t.exit2_qty, t.exit2_qty, 'number')}</td>

                    {/* 계산값 (읽기전용) */}
                    <td>{fmtRate(rate) ?? <span className="td-na">-</span>}</td>
                    <td>{fmtAmount(amount, t.ticker) ?? <span className="td-na">-</span>}</td>

                    {/* 반등 체크 */}
                    <td className="td-num">
                      <input type="checkbox"
                        className="cell-checkbox"
                        checked={!!t.rebound_after_stop}
                        onChange={e => updateMutation.mutate({ id: t.id, col: 'rebound_after_stop', value: String(e.target.checked) })}
                        onClick={e => e.stopPropagation()}
                      />
                    </td>

                    {/* 메모 */}
                    <td className="td-memo">{C(t.id, 'memo', t.memo, t.memo ?? '', 'text')}</td>

                    {/* 삭제 */}
                    <td>
                      <button className="journal-del-btn"
                        onClick={e => { e.stopPropagation(); deleteMutation.mutate(t.id) }}>
                        ✕
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
