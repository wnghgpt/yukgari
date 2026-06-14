import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/stock'
import { useAppStore } from '../../store'
import type { JournalPayload } from '../calculator/StrategyTab'
import './JournalDirectForm.css'

const PATTERNS = ['손잡이컵', '손잡이컵 (놓침)', '역추세', '우량주', '횡보돌파', '횡보돌파 (놓침)']
const RESULTS  = ['감시', '보유', '수익', '손절']

interface Props {
  ticker: string
  name?: string
  defaultPattern: string
  payload: JournalPayload | null
  isOverseas: boolean
  onSave: () => void
  onCancel: () => void
}

export function JournalDirectForm({ ticker, name, defaultPattern, payload, isOverseas, onSave, onCancel }: Props) {
  const queryClient = useQueryClient()
  const { userId, setSidebarTab, setMySubTab } = useAppStore()
  const step = isOverseas ? 0.01 : 10

  const initPrices  = payload?.entryPrices ?? [0, 0, 0]
  const initWeights = payload?.quantities.map(Math.floor) ?? [0, 0, 0]

  const [form, setForm] = useState({
    ticker,
    pattern:       defaultPattern,
    channel_top:   payload?.resistPrice  ?? 0,
    channel_bottom: payload?.supportPrice ?? 0,
    entry_prices:  initPrices,
    entry_weights: initWeights,
    stop_loss:     payload?.stopLoss     ?? 0,
    target_price:  payload?.targetPrice  ?? 0,
    date:          new Date().toISOString().split('T')[0],
    result:        '감시',
    memo:          '',
  })

  const set = (key: string, value: unknown) =>
    setForm(f => ({ ...f, [key]: value }))

  const setEntry = (idx: number, field: 'p' | 'w', v: number) =>
    setForm(f => {
      const prices  = field === 'p' ? [...f.entry_prices]  : f.entry_prices
      const weights = field === 'w' ? [...f.entry_weights] : f.entry_weights
      if (field === 'p') prices[idx]  = v
      else               weights[idx] = v
      return { ...f, entry_prices: prices, entry_weights: weights }
    })

  const mutation = useMutation({
    mutationFn: () => {
      const body: Record<string, unknown> = {
        ticker:        form.ticker,
        name:          name ?? form.ticker,
        pattern:       form.pattern,
        date:          form.date,
        stages:        form.entry_prices.filter(p => p > 0).length || form.entry_prices.length,
        channel_top:   form.channel_top   || null,
        channel_bottom: form.channel_bottom || null,
        stop_loss:     form.stop_loss     || null,
        target_price:  form.target_price  || null,
        result:        form.result,
        memo:          form.memo          || null,
      }
      form.entry_prices.forEach((p, i)  => { body[`entry${i + 1}_price`]  = p || null })
      form.entry_weights.forEach((w, i) => { body[`entry${i + 1}_weight`] = w || null })
      return api.addJournal(body, userId!)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journal', userId] })
      setSidebarTab('my')
      setMySubTab('감시')
      onSave()
    },
    onError: (e: Error) => alert(`일지 저장 실패: ${e.message}`),
  })

  return (
    <div className="jdf">
      <div className="jdf-header">
        <button className="jdf-back" onClick={onCancel}>← 계산기</button>
        <span className="jdf-title">일지 직접 입력</span>
      </div>

      <div className="jdf-body">
        <div className="jdf-row">
          <label className="jdf-label">종목</label>
          <input className="jdf-input" value={form.ticker}
            onChange={e => set('ticker', e.target.value)} />
        </div>

        <div className="jdf-row">
          <label className="jdf-label">패턴</label>
          <select className="jdf-input" value={form.pattern}
            onChange={e => set('pattern', e.target.value)}>
            {PATTERNS.map(p => <option key={p}>{p}</option>)}
          </select>
        </div>

        <div className="jdf-row">
          <label className="jdf-label">저항선</label>
          <input className="jdf-input" type="number" step={step}
            value={form.channel_top || ''}
            onChange={e => set('channel_top', +e.target.value)} />
        </div>

        <div className="jdf-row">
          <label className="jdf-label">지지선</label>
          <input className="jdf-input" type="number" step={step}
            value={form.channel_bottom || ''}
            onChange={e => set('channel_bottom', +e.target.value)} />
        </div>

        <hr className="jdf-divider" />

        {form.entry_prices.map((price, i) => (
          <div key={i} className="jdf-row">
            <label className="jdf-label">{i + 1}차</label>
            <input className="jdf-input jdf-half" type="number" step={step}
              value={price || ''} placeholder="가격"
              onChange={e => setEntry(i, 'p', +e.target.value)} />
            <input className="jdf-input jdf-qty" type="number" step={1}
              value={form.entry_weights[i] || ''} placeholder="주"
              onChange={e => setEntry(i, 'w', +e.target.value)} />
          </div>
        ))}

        <hr className="jdf-divider" />

        <div className="jdf-row">
          <label className="jdf-label">손절</label>
          <input className="jdf-input" type="number" step={step}
            value={form.stop_loss || ''}
            onChange={e => set('stop_loss', +e.target.value)} />
        </div>

        <div className="jdf-row">
          <label className="jdf-label">목표가</label>
          <input className="jdf-input" type="number" step={step}
            value={form.target_price || ''}
            onChange={e => set('target_price', +e.target.value)} />
        </div>

        <hr className="jdf-divider" />

        <div className="jdf-row">
          <label className="jdf-label">진입일</label>
          <input className="jdf-input" type="date" value={form.date}
            onChange={e => set('date', e.target.value)} />
        </div>

        <div className="jdf-row">
          <label className="jdf-label">결과</label>
          <select className="jdf-input" value={form.result}
            onChange={e => set('result', e.target.value)}>
            {RESULTS.map(r => <option key={r}>{r}</option>)}
          </select>
        </div>

        <div className="jdf-row">
          <label className="jdf-label">메모</label>
          <input className="jdf-input" type="text" value={form.memo}
            placeholder="선택사항"
            onChange={e => set('memo', e.target.value)} />
        </div>

        <button className="jdf-save-btn" onClick={() => mutation.mutate()}
          disabled={mutation.isPending}>
          {mutation.isPending ? '저장 중...' : '💾 저장'}
        </button>
        {mutation.isError && <p className="jdf-error">저장 실패. 다시 시도해주세요.</p>}
      </div>
    </div>
  )
}
