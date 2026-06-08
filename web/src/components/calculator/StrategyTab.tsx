import { useState, useEffect, useMemo, useRef } from 'react'
import { useAppStore } from '../../store'
import { calcBreakout, calcZone, fmtPrice, fmtAmount, type CalcResult } from '../../lib/calculator'
import { Indicators } from './Indicators'
import type { ScenarioData } from '../../types'

export type StrategyMode = 'breakout' | 'zone' | 'forceZone'

function buildScenario(
  isZone: boolean,
  missed: boolean,
  currentPrice: number,
  resistPrice: number,
  supportPrice: number,
  result: CalcResult,
): ScenarioData {
  const entries = result.entryPrices
  const target  = result.targetPrice
  const ZONE_BARS = [5, 10, 15]

  const base = {
    resistPrice: result.isZone ? resistPrice : resistPrice,
    supportPrice: isZone ? supportPrice : undefined,
    targetPrice: target,
    stopLoss: result.stopLoss,
  }

  if (!isZone && !missed) {
    const surgePeak = resistPrice * 1.10
    return {
      ...base,
      points: [
        { barOffset: 0,  price: currentPrice },
        { barOffset: 8,  price: entries[0] },   // 1차 (저항+2%)
        { barOffset: 15, price: surgePeak },     // 급등 (저항+10%)
        { barOffset: 22, price: entries[1] ?? entries[0] }, // 2차 풀백 (저항-2%)
        { barOffset: 45, price: target },
      ],
      entries: entries.map((p, i) => ({
        barOffset: i === 0 ? 8 : 22,
        price: p,
        nth: i + 1,
      })),
    }
  }

  return {
    ...base,
    points: [
      { barOffset: 0, price: currentPrice },
      ...entries.map((p, i) => ({ barOffset: ZONE_BARS[i] ?? (i + 1) * 5, price: p })),
      { barOffset: 50, price: target },
    ],
    entries: entries.map((p, i) => ({
      barOffset: ZONE_BARS[i] ?? (i + 1) * 5,
      price: p,
      nth: i + 1,
    })),
  }
}

interface Props {
  symbol: string
  defaultSlPct: number
  missedSlPct: number
  mode: StrategyMode
  rrMultiple: number
  currentPrice: number
  isOverseas: boolean
  allowedLoss: number
  onJournalAdd?: (data: JournalPayload) => void
  onDirectEntry?: (data: JournalPayload | null) => void
}

export interface JournalPayload {
  resistPrice: number
  supportPrice: number
  stopLoss: number
  targetPrice: number
  entryPrices: number[]
  quantities: number[]
  missed: boolean
}

export function StrategyTab({
  symbol, defaultSlPct, missedSlPct, mode,
  rrMultiple, currentPrice, isOverseas, allowedLoss, onJournalAdd, onDirectEntry,
}: Props) {
  const { setScenario, scenarioDrag, setScenarioDrag } = useAppStore()
  const priceStep = isOverseas ? 0.01 : 100

  const [showScenario, setShowScenario] = useState(false)
  const [missed, setMissed]             = useState(mode === 'forceZone')
  const [resistPrice, setResist]  = useState(0)
  const [supportPrice, setSupport]= useState(0)
  const [slPct, setSlPct]         = useState(defaultSlPct)

  // 심볼 변경 시만 초기화, websocket 업데이트는 무시
  const prevSymbolRef  = useRef('')
  const initializedRef = useRef(false)
  useEffect(() => {
    if (symbol !== prevSymbolRef.current) {
      prevSymbolRef.current = symbol
      initializedRef.current = false
    }
    if (!initializedRef.current && currentPrice > 0) {
      initializedRef.current = true
      setResist(isOverseas ? +currentPrice.toFixed(2) : Math.round(currentPrice))
      setSupport(isOverseas ? +(currentPrice * 0.9).toFixed(2) : Math.round(currentPrice * 0.9))
    }
  }, [symbol, currentPrice, isOverseas])

  const isZone = mode === 'forceZone' || (mode === 'zone' && missed)

  const result = useMemo<CalcResult | null>(() => {
    return isZone
      ? calcZone({ resistPrice, supportPrice, missedSlPct, rrMultiple, allowedLoss, isOverseas })
      : calcBreakout({ resistPrice, missed, slPct, missedSlPct, rrMultiple, allowedLoss, isOverseas })
  }, [isZone, resistPrice, supportPrice, missedSlPct, rrMultiple, allowedLoss, isOverseas, missed, slPct])

  // 시나리오 오버레이 동기화
  useEffect(() => {
    if (!showScenario || !result || currentPrice <= 0) {
      setScenario(null)
      return
    }
    setScenario(buildScenario(isZone, missed, currentPrice, resistPrice, supportPrice, result))
  }, [showScenario, result, isZone, missed, currentPrice, resistPrice, supportPrice]) // eslint-disable-line react-hooks/exhaustive-deps

  // 드래그 피드백 수신 (ChartView → StrategyTab)
  useEffect(() => {
    if (!scenarioDrag || !showScenario) return
    if (scenarioDrag.resistPrice !== undefined) setResist(scenarioDrag.resistPrice)
    if (scenarioDrag.supportPrice !== undefined) setSupport(scenarioDrag.supportPrice)
    setScenarioDrag(null)
  }, [scenarioDrag, showScenario]) // eslint-disable-line react-hooks/exhaustive-deps

  // 탭 언마운트 시 클리어
  useEffect(() => () => { setScenario(null) }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // 전략 설명 텍스트
  const stratDesc = useMemo(() => {
    if (!missed && mode === 'breakout') {
      return {
        buy:   '저항선+2% 1차 / 저항선-2% 2차',
        ratio: '70:30',
        sl:    `저항선-${slPct.toFixed(0)}% 손절`,
      }
    }
    if (isZone) {
      return {
        buy:   '1/3점 / 2/3점 / 지지선',
        ratio: '20:30:50',
        sl:    `평단-${missedSlPct.toFixed(0)}% 손절`,
      }
    }
    return {
      buy:   '저항선+4% / +1% / -2%',
      ratio: '30:40:30',
      sl:    `저항선-${slPct.toFixed(0)}% 손절`,
    }
  }, [missed, mode, isZone, slPct, missedSlPct])

  const fmtP = (v: number) => fmtPrice(v, isOverseas)
  const fmtA = (v: number) => fmtAmount(v, isOverseas)
  const dropPct = (price: number) =>
    currentPrice > 0 ? ((price / currentPrice) - 1) * 100 : 0

  return (
    <div className="strategy-tab">

      {/* 토글 */}
      <div className="strat-row strat-toggles">
        {mode !== 'forceZone' && (
          <label className="strat-toggle">
            <input type="checkbox" checked={missed}
              onChange={e => setMissed(e.target.checked)} />
            돌파놓침
          </label>
        )}
        {result && (
          <label className="strat-toggle">
            <input type="checkbox" checked={showScenario}
              onChange={e => setShowScenario(e.target.checked)} />
            시나리오
          </label>
        )}
      </div>

      {/* 전략 요약 (항상 표시) */}
      <div className="strat-strategy-desc">
        <div className="strat-desc-row">
          <span className="desc-key">매수</span>
          <span className="desc-val">{stratDesc.buy}</span>
          <span className="desc-ratio">{stratDesc.ratio}</span>
        </div>
        <div className="strat-desc-row">
          <span className="desc-key">매도</span>
          <span className="desc-sl">{stratDesc.sl}</span>
        </div>
        <div className="strat-desc-row">
          <span className="desc-key">목표가</span>
          <span className="desc-target">
            {result ? `평단+${(rrMultiple * result.lossPct).toFixed(0)}%` : '—'}
          </span>
          <span className="desc-rr">손익비 {rrMultiple}x</span>
        </div>
      </div>

      {/* 입력 필드 */}
      <div className="strat-row">
        <label className="strat-label">저항선</label>
        <input
          type="number" className="strat-input"
          value={resistPrice || ''} step={priceStep} placeholder="0"
          onChange={e => setResist(e.target.value === '' ? 0 : +e.target.value)}
        />
      </div>

      {isZone && (
        <div className="strat-row">
          <label className="strat-label">지지선</label>
          <input
            type="number" className="strat-input"
            value={supportPrice || ''} step={priceStep} placeholder="0"
            onChange={e => setSupport(e.target.value === '' ? 0 : +e.target.value)}
          />
        </div>
      )}

      {!isZone && (
        <div className="strat-row">
          <label className="strat-label">손절</label>
          <input
            type="number" className="strat-input strat-input-sm"
            value={slPct} step={0.1} min={0} max={30}
            onChange={e => setSlPct(+e.target.value)}
          />
          <span className="strat-unit">%</span>
        </div>
      )}

      <hr className="strat-divider" />

      {/* 입력 안내 */}
      {!result && (
        <p className="strat-hint">
          {isZone && resistPrice > 0 && supportPrice <= 0
            ? '지지선을 입력하세요'
            : isZone && resistPrice > 0 && resistPrice <= supportPrice
            ? '저항선 > 지지선 조건 확인'
            : '저항선을 입력하면 시뮬레이션이 표시됩니다'}
        </p>
      )}

      {/* 결과 */}
      {result && (
        <div className="strat-result">

          {/* 투입 + 평단 요약 */}
          <div className="strat-summary">
            <span>평단 <b>{fmtP(result.avgPrice)}</b></span>
            <span>투입 <b>{fmtA(result.budget)}</b> ({Math.round(result.quantities.reduce((a, b) => a + b, 0)).toLocaleString()}주)</span>
          </div>

          {/* 차수별 + 손절/목표가 */}
          <div className="strat-entries">
            {result.entryPrices.map((price, i) => {
              const dp = dropPct(price)
              return (
                <div key={i} className="strat-entry-row">
                  <span className="entry-nth">{i + 1}차</span>
                  <span className="entry-price">{fmtP(price)}</span>
                  <span className={`entry-drop ${dp >= 0 ? 'up' : 'down'}`}>
                    ({dp >= 0 ? '+' : ''}{dp.toFixed(1)}%)
                  </span>
                  <span className="entry-qty">{Math.floor(result.quantities[i]).toLocaleString()}주</span>
                  <span className="entry-amt">{fmtA(result.amounts[i])}</span>
                </div>
              )
            })}

            <div className="strat-entry-row strat-sl-row">
              <span className="entry-nth">손절</span>
              <span className="entry-price">{fmtP(result.stopLoss)}</span>
              <span className="entry-drop down">(-{result.lossPct.toFixed(1)}%)</span>
            </div>

            <div className="strat-entry-row strat-target-row">
              <span className="entry-nth">목표</span>
              <span className="entry-price">{fmtP(result.targetPrice)}</span>
              <span className="entry-drop up">(+{(rrMultiple * result.lossPct).toFixed(1)}%)</span>
              <span className="entry-rr">RR {result.rrMultiple}x</span>
            </div>
          </div>

        </div>
      )}

      {/* 보조지표 */}
      <Indicators symbol={symbol} />

      {/* 일지 버튼 */}
      {result && (
        <div className="journal-btns">
          <button
            className="journal-add-btn"
            onClick={() => onJournalAdd?.({
              resistPrice, supportPrice,
              stopLoss: result.stopLoss,
              targetPrice: result.targetPrice,
              entryPrices: result.entryPrices,
              quantities: result.quantities,
              missed,
            })}
          >
            📒 일지에 추가
          </button>
          <button
            className="journal-direct-btn"
            onClick={() => onDirectEntry?.({
              resistPrice, supportPrice,
              stopLoss: result.stopLoss,
              targetPrice: result.targetPrice,
              entryPrices: result.entryPrices,
              quantities: result.quantities,
              missed,
            })}
          >
            📝 일지 직접 입력
          </button>
        </div>
      )}
    </div>
  )
}
