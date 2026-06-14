import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  LineStyle,
  type IChartApi,
  type Logical,
} from 'lightweight-charts'
import { api } from '../../api/stock'
import { useAppStore } from '../../store'
import { useWatchlist } from '../../hooks/useWatchlist'
import { StockSearch } from './StockSearch'
import type { Period, DrawnLine, JournalTrade } from '../../types'
import './ChartView.css'

// ── helpers ──────────────────────────────────────────────

const MA_COLORS: Record<number, string> = {
  5: '#FF1744', 20: '#FF9800', 60: '#2ECC71', 120: '#9B59B6', 240: '#808080',
}
const MA_PERIODS = [5, 20, 60, 120, 240]

function calcMa(closes: number[], period: number): (number | null)[] {
  return closes.map((_, i) => {
    if (i < period - 1) return null
    let sum = 0
    for (let j = i - period + 1; j <= i; j++) sum += closes[j]
    return sum / period
  })
}

function calcRsi(closes: number[], period = 14): (number | null)[] {
  if (closes.length < period + 1) return closes.map(() => null)
  const out: (number | null)[] = new Array(period).fill(null)
  let ag = 0, al = 0
  for (let i = 1; i <= period; i++) {
    const d = closes[i] - closes[i - 1]
    if (d > 0) ag += d; else al -= d
  }
  ag /= period; al /= period
  out.push(al === 0 ? 100 : 100 - 100 / (1 + ag / al))
  for (let i = period + 1; i < closes.length; i++) {
    const d = closes[i] - closes[i - 1]
    ag = (ag * (period - 1) + (d > 0 ? d : 0)) / period
    al = (al * (period - 1) + (d < 0 ? -d : 0)) / period
    out.push(al === 0 ? 100 : 100 - 100 / (1 + ag / al))
  }
  return out
}

const BASE_CHART_OPTS = {
  layout: { background: { color: '#131722' }, textColor: '#d1d4dc', fontSize: 9 },
  grid: {
    vertLines: { color: 'transparent' },
    horzLines: { color: 'rgba(42,46,57,0.5)' },
  },
  crosshair: { mode: 0 },
  timeScale: { borderColor: 'rgba(197,203,206,0.8)', rightOffset: 40 },
}

function distToSegment(px: number, py: number, x1: number, y1: number, x2: number, y2: number) {
  const dx = x2 - x1, dy = y2 - y1
  const lenSq = dx * dx + dy * dy
  if (lenSq === 0) return Math.hypot(px - x1, py - y1)
  const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / lenSq))
  return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
}

// ── component ─────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyS = any

interface SeriesStore {
  candle: AnyS
  volume: AnyS
  mas: Record<number, AnyS>
  rsi: AnyS
  rsi70: AnyS
  rsi30: AnyS
}

export function ChartView() {
  const mainRef          = useRef<HTMLDivElement>(null)
  const rsiRef           = useRef<HTMLDivElement>(null)
  const scenarioCanvasRef = useRef<HTMLCanvasElement>(null)
  const chartRef = useRef<{ main: IChartApi | null; rsi: IChartApi | null }>({ main: null, rsi: null })
  const s = useRef<SeriesStore | null>(null)

  const { symbol, symbolName, period, setPeriod, scenario, setScenarioDrag,
          drawnLines, addDrawnLine, removeDrawnLine, clearDrawnLines,
          livePrices, prevCloses, setPrevClose,
          selectedTradeId, userId } = useAppStore()
  const queryClient = useQueryClient()
  const scenarioRef       = useRef(scenario)
  const tradeScenarioRef  = useRef<{ trade: JournalTrade; tradeBarIndex: number; startPrice: number } | null>(null)
  const dataLengthRef     = useRef(0)
  const drawFnRef         = useRef<() => void>(() => {})
  const syncHandlesFnRef  = useRef<() => void>(() => {})
  const isOverseasRef     = useRef(false)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const scenarioPLinesRef = useRef<Record<string, any>>({})
  const resistHandleRef   = useRef<HTMLDivElement>(null)
  const supportHandleRef  = useRef<HTMLDivElement>(null)
  const drawnLinesRef     = useRef<Record<string, DrawnLine[]>>({})
  const symbolRef         = useRef(symbol)
  const drawingModeRef    = useRef<'none' | 'segment'>('none')
  const segmentStartRef   = useRef<{ barOffset: number; price: number; px: number; py: number } | null>(null)
  const isDrawingRef      = useRef(false)
  const drawTempRef       = useRef<{ x1: number; y1: number; x2: number; y2: number } | null>(null)
  const crosshairBtnRef   = useRef<HTMLDivElement>(null)
  const crosshairPriceRef = useRef<number | null>(null)
  const displayPriceRef   = useRef<number | null>(null)

  const [count, setCount] = useState(900)
  const [showRsi, setShowRsi] = useState(true)
  const [showMa,  setShowMa]  = useState(true)
  const [drawingMode, setDrawingModeState] = useState<'none' | 'segment'>('none')
  const setDrawingMode = (m: 'none' | 'segment') => {
    drawingModeRef.current = m
    setDrawingModeState(m)
  }

  const { data, isLoading } = useQuery({
    queryKey: ['ohlcv', symbol, count, period],
    queryFn: () => api.ohlcv(symbol, count, period),
    enabled: !!symbol,
  })

  // ── init charts & series (once) ──
  useEffect(() => {
    if (!mainRef.current || !rsiRef.current) return

    const main = createChart(mainRef.current, {
      ...BASE_CHART_OPTS,
      width:  mainRef.current.clientWidth,
      height: mainRef.current.clientHeight || 400,
    })
    const rsiChart = createChart(rsiRef.current, {
      ...BASE_CHART_OPTS,
      width:  rsiRef.current.clientWidth,
      height: 80,
      timeScale: { ...BASE_CHART_OPTS.timeScale, visible: false },
      rightPriceScale: { borderVisible: false },
    })

    // Sync timescales (bidirectional)
    let syncing = false
    main.timeScale().subscribeVisibleLogicalRangeChange((r) => {
      if (syncing || !r) return
      syncing = true
      rsiChart.timeScale().setVisibleLogicalRange(r)
      syncing = false
    })
    rsiChart.timeScale().subscribeVisibleLogicalRangeChange((r) => {
      if (syncing || !r) return
      syncing = true
      main.timeScale().setVisibleLogicalRange(r)
      syncing = false
    })

    // Candle series (hollow style)
    const candle = main.addSeries(CandlestickSeries, {
      upColor: 'rgba(0,0,0,0)',
      downColor: 'rgba(0,0,0,0)',
      borderVisible: true,
      borderUpColor: '#ef5350',
      borderDownColor: '#2196F3',
      wickUpColor: '#ef5350',
      wickDownColor: '#2196F3',
      lastValueVisible: false,
      priceLineVisible: false,
    })

    // Volume (overlay, bottom 20%)
    const volume = main.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'vol',
    })
    main.priceScale('vol').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    // MA series
    const mas: Record<number, AnyS> = {}
    for (const p of MA_PERIODS) {
      mas[p] = main.addSeries(LineSeries, {
        color: MA_COLORS[p],
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
        visible: true,
      })
    }

    // RSI series
    const rsiLine = rsiChart.addSeries(LineSeries, {
      color: '#9B59B6',
      lineWidth: 1,
      title: 'RSI(14)',
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: false,
    })
    const rsi70 = rsiChart.addSeries(LineSeries, {
      color: '#ef5350',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })
    const rsi30 = rsiChart.addSeries(LineSeries, {
      color: '#3498DB',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })

    chartRef.current = { main, rsi: rsiChart }
    s.current = { candle, volume, mas, rsi: rsiLine, rsi70, rsi30 }

    const syncScenarioCanvas = () => {
      const canvas = scenarioCanvasRef.current
      const wrap   = mainRef.current
      if (!canvas || !wrap || !wrap.clientWidth || !wrap.clientHeight) return
      const w = wrap.clientWidth
      const h = wrap.clientHeight
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width  = w   // canvas.width 변경은 자동으로 캔버스를 지움
        canvas.height = h
      }
      drawFnRef.current()   // 크기 변경 후 반드시 재드로우
    }

    const drawScenario = () => {
      const canvas = scenarioCanvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      const ser = s.current
      if (!ser) return

      const sc  = scenarioRef.current
      const ts  = main.timeScale()
      const lastLogical = dataLengthRef.current - 1

      const toXY = (barOffset: number, price: number) => ({
        x: ts.logicalToCoordinate((lastLogical + barOffset) as unknown as Logical) as number | null,
        y: ser.candle.priceToCoordinate(price)             as number | null,
      })

      if (sc) {
        // 경로 (꺾인선 + 화살표)
        const pts = sc.points
          .map(p => toXY(p.barOffset, p.price))
          .filter((p): p is { x: number; y: number } => p.x != null && p.y != null)

        if (pts.length >= 2) {
          ctx.save()
          ctx.strokeStyle = '#FFD700'
          ctx.lineWidth   = 2
          ctx.setLineDash([6, 3])
          ctx.beginPath()
          ctx.moveTo(pts[0].x, pts[0].y)
          for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y)
          ctx.stroke()
          ctx.setLineDash([])

          // 끝점 화살표
          const last = pts[pts.length - 1]
          const prev = pts[pts.length - 2]
          const angle = Math.atan2(last.y - prev.y, last.x - prev.x)
          const sz = 10
          ctx.fillStyle = '#FFD700'
          ctx.beginPath()
          ctx.moveTo(last.x, last.y)
          ctx.lineTo(last.x - sz * Math.cos(angle - Math.PI / 6), last.y - sz * Math.sin(angle - Math.PI / 6))
          ctx.lineTo(last.x - sz * Math.cos(angle + Math.PI / 6), last.y - sz * Math.sin(angle + Math.PI / 6))
          ctx.closePath()
          ctx.fill()
          ctx.restore()
        }

        // 매수 마커 (핑크)
        for (const entry of sc.entries) {
          const { x, y } = toXY(entry.barOffset, entry.price)
          if (x == null || y == null) continue
          ctx.save()
          ctx.beginPath()
          ctx.arc(x, y, 5, 0, Math.PI * 2)
          ctx.fillStyle = '#ec4899'
          ctx.fill()
          ctx.font      = 'bold 10px sans-serif'
          ctx.fillStyle = '#ec4899'
          ctx.fillText(`${entry.nth}차`, x + 7, y + 4)
          ctx.restore()
        }

        // 평단 수평선 (현재 바 ~ 오른쪽 끝, 가격 태그 없음)
        if (sc.avgPrice > 0) {
          const originPt = toXY(0, sc.avgPrice)
          if (originPt.x != null && originPt.y != null) {
            ctx.save()
            ctx.strokeStyle = '#FF9800'
            ctx.lineWidth = 1.5
            ctx.setLineDash([5, 3])
            ctx.beginPath()
            ctx.moveTo(originPt.x, originPt.y)
            ctx.lineTo(canvas.width, originPt.y)
            ctx.stroke()
            ctx.restore()
          }
        }
      }

      // 등록 시나리오 (selectedTrade 기준, 등록일 종가에 앵커)
      const tsc = tradeScenarioRef.current
      if (tsc && tsc.trade.ticker === symbolRef.current) {
        const { trade, tradeBarIndex, startPrice } = tsc
        const ENTRY_COLORS = ['#3b82f6', '#60a5fa', '#2ecc71', '#a78bfa']

        const absXY = (absIdx: number, price: number) => ({
          x: ts.logicalToCoordinate(absIdx as unknown as Logical) as number | null,
          y: ser.candle.priceToCoordinate(price) as number | null,
        })

        const startPt = absXY(tradeBarIndex, startPrice)

        // 경로: 시작 → 저항선(5봉 후) → 목표가(30봉 후)
        const pathPts: { x: number; y: number }[] = []
        if (startPt.x != null && startPt.y != null)
          pathPts.push({ x: startPt.x, y: startPt.y })
        if (trade.channel_top) {
          const p = absXY(tradeBarIndex + 5, trade.channel_top)
          if (p.x != null && p.y != null) pathPts.push({ x: p.x, y: p.y })
        }
        if (trade.target_price) {
          const p = absXY(tradeBarIndex + 30, trade.target_price)
          if (p.x != null && p.y != null) pathPts.push({ x: p.x, y: p.y })
        }

        if (pathPts.length >= 2) {
          ctx.save()
          ctx.strokeStyle = '#FFD700'
          ctx.lineWidth = 1.5
          ctx.setLineDash([6, 3])
          ctx.beginPath()
          ctx.moveTo(pathPts[0].x, pathPts[0].y)
          for (let i = 1; i < pathPts.length; i++) ctx.lineTo(pathPts[i].x, pathPts[i].y)
          ctx.stroke()
          ctx.setLineDash([])
          const last = pathPts[pathPts.length - 1]
          const prev = pathPts[pathPts.length - 2]
          const angle = Math.atan2(last.y - prev.y, last.x - prev.x)
          const sz = 8
          ctx.fillStyle = '#FFD700'
          ctx.beginPath()
          ctx.moveTo(last.x, last.y)
          ctx.lineTo(last.x - sz * Math.cos(angle - Math.PI / 6), last.y - sz * Math.sin(angle - Math.PI / 6))
          ctx.lineTo(last.x - sz * Math.cos(angle + Math.PI / 6), last.y - sz * Math.sin(angle + Math.PI / 6))
          ctx.closePath()
          ctx.fill()
          ctx.restore()
        }

        // 손절 수평선 (빨강 점선)
        if (trade.stop_loss && startPt.x != null) {
          const slY = ser.candle.priceToCoordinate(trade.stop_loss) as number | null
          if (slY != null) {
            ctx.save()
            ctx.strokeStyle = '#ef4444'
            ctx.lineWidth = 1
            ctx.setLineDash([4, 3])
            ctx.beginPath()
            ctx.moveTo(startPt.x, slY)
            ctx.lineTo(canvas.width, slY)
            ctx.stroke()
            ctx.setLineDash([])
            ctx.fillStyle = '#ef4444'
            ctx.font = '9px sans-serif'
            ctx.fillText('손절', startPt.x + 4, slY - 3)
            ctx.restore()
          }
        }

        // 목표가 수평선 (초록 점선)
        if (trade.target_price && startPt.x != null) {
          const tpY = ser.candle.priceToCoordinate(trade.target_price) as number | null
          if (tpY != null) {
            ctx.save()
            ctx.strokeStyle = '#2ecc71'
            ctx.lineWidth = 1
            ctx.setLineDash([4, 3])
            ctx.beginPath()
            ctx.moveTo(startPt.x, tpY)
            ctx.lineTo(canvas.width, tpY)
            ctx.stroke()
            ctx.setLineDash([])
            ctx.fillStyle = '#2ecc71'
            ctx.font = '9px sans-serif'
            ctx.fillText('목표', startPt.x + 4, tpY - 3)
            ctx.restore()
          }
        }

        // 차수 도트 (entry1~4)
        for (let i = 1; i <= 4; i++) {
          const price = trade[`entry${i}_price` as keyof JournalTrade] as number | undefined
          if (!price) continue
          const ep = absXY(tradeBarIndex + (i - 1) * 3 + 2, price)
          if (ep.x == null || ep.y == null) continue
          ctx.save()
          ctx.beginPath()
          ctx.arc(ep.x, ep.y, 4, 0, Math.PI * 2)
          ctx.fillStyle = ENTRY_COLORS[i - 1]
          ctx.fill()
          ctx.font = 'bold 9px sans-serif'
          ctx.fillStyle = ENTRY_COLORS[i - 1]
          ctx.fillText(`${i}차`, ep.x + 6, ep.y + 3)
          ctx.restore()
        }

        // 시작점 도트 (등록일)
        if (startPt.x != null && startPt.y != null) {
          ctx.save()
          ctx.beginPath()
          ctx.arc(startPt.x, startPt.y, 5, 0, Math.PI * 2)
          ctx.fillStyle = '#131722'
          ctx.fill()
          ctx.strokeStyle = '#FFD700'
          ctx.lineWidth = 2
          ctx.stroke()
          ctx.restore()
        }
      }

      // 유저 드로잉 라인
      const userLines = drawnLinesRef.current[symbolRef.current] ?? []
      for (const line of userLines) {
        ctx.save()
        ctx.strokeStyle = line.color
        if (line.type === 'horizontal' && line.price != null) {
          const uy = ser.candle.priceToCoordinate(line.price) as number | null
          if (uy != null) {
            const TAG_W = 56, TAG_H = 16
            const label = isOverseasRef.current
              ? line.price.toFixed(2)
              : Math.round(line.price).toLocaleString()
            // 태그: 왼쪽 끝
            ctx.fillStyle = '#1a1a1a'
            ctx.beginPath()
            ctx.roundRect(0, uy - TAG_H / 2, TAG_W, TAG_H, 3)
            ctx.fill()
            ctx.strokeStyle = line.color
            ctx.lineWidth = 1
            ctx.stroke()
            ctx.fillStyle = line.color
            ctx.font = 'bold 10px sans-serif'
            ctx.textAlign = 'center'
            ctx.textBaseline = 'middle'
            ctx.fillText(label, TAG_W / 2, uy, TAG_W - 4)
            // 선: 태그 오른쪽 끝 ~ 캔버스 오른쪽 끝
            ctx.setLineDash([5, 3])
            ctx.beginPath()
            ctx.moveTo(TAG_W, uy)
            ctx.lineTo(canvas.width, uy)
            ctx.stroke()
            ctx.setLineDash([])
          }
        } else if (
          line.type === 'segment' &&
          line.barOffset1 != null && line.price1 != null &&
          line.barOffset2 != null && line.price2 != null
        ) {
          const ux1 = ts.logicalToCoordinate((lastLogical + line.barOffset1) as unknown as Logical) as number | null
          const uy1 = ser.candle.priceToCoordinate(line.price1) as number | null
          const ux2 = ts.logicalToCoordinate((lastLogical + line.barOffset2) as unknown as Logical) as number | null
          const uy2 = ser.candle.priceToCoordinate(line.price2) as number | null
          if (ux1 != null && uy1 != null && ux2 != null && uy2 != null) {
            ctx.lineWidth = 1.5
            ctx.beginPath()
            ctx.moveTo(ux1, uy1)
            ctx.lineTo(ux2, uy2)
            ctx.stroke()
          }
        }
        ctx.restore()
      }

      // 현재가 Y축 태그 (LW 내장 태그 대신 캔버스에 직접 그려 충돌 회피 없음)
      const curPrice = displayPriceRef.current
      if (curPrice != null) {
        const cy = ser.candle.priceToCoordinate(curPrice) as number | null
        if (cy != null) {
          const TAG_W = 60, TAG_H = 16
          const label = isOverseasRef.current
            ? curPrice.toFixed(2)
            : Math.round(curPrice).toLocaleString()
          ctx.save()
          ctx.fillStyle = '#1f2937'
          ctx.beginPath()
          ctx.roundRect(canvas.width - TAG_W, cy - TAG_H / 2, TAG_W, TAG_H, 3)
          ctx.fill()
          ctx.strokeStyle = '#9ca3af'
          ctx.lineWidth = 1
          ctx.stroke()
          ctx.fillStyle = '#e5e7eb'
          ctx.font = 'bold 10px sans-serif'
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(label, canvas.width - TAG_W / 2, cy, TAG_W - 4)
          ctx.restore()
        }
      }

      // 임시 선분 (그리는 중)
      const temp = drawTempRef.current
      if (temp) {
        ctx.save()
        ctx.strokeStyle = '#e2e8f0'
        ctx.lineWidth = 1.5
        ctx.setLineDash([4, 2])
        ctx.beginPath()
        ctx.moveTo(temp.x1, temp.y1)
        ctx.lineTo(temp.x2, temp.y2)
        ctx.stroke()
        ctx.setLineDash([])
        ctx.restore()
      }
    }

    const syncHandles = () => {
      const ser = s.current
      const sc  = scenarioRef.current
      const rh  = resistHandleRef.current
      const sh  = supportHandleRef.current
      if (!ser || !sc) {
        if (rh) rh.style.display = 'none'
        if (sh) sh.style.display = 'none'
        return
      }
      const ry = ser.candle.priceToCoordinate(sc.resistPrice) as number | null
      if (rh) {
        if (ry != null) { rh.style.top = `${ry}px`; rh.style.display = 'block' }
        else rh.style.display = 'none'
      }
      const sy = sc.supportPrice != null
        ? ser.candle.priceToCoordinate(sc.supportPrice) as number | null
        : null
      if (sh) {
        if (sy != null) { sh.style.top = `${sy}px`; sh.style.display = 'block' }
        else sh.style.display = 'none'
      }
    }

    drawFnRef.current        = drawScenario
    syncHandlesFnRef.current = syncHandles
    main.timeScale().subscribeVisibleLogicalRangeChange(() => {
      drawFnRef.current()
      syncHandlesFnRef.current()
    })

    const ro = new ResizeObserver(() => {
      if (mainRef.current) main.applyOptions({
        width:  mainRef.current.clientWidth,
        height: mainRef.current.clientHeight,
      })
      if (rsiRef.current && rsiRef.current.clientWidth > 0) rsiChart.applyOptions({
        width: rsiRef.current.clientWidth,
      })
      syncScenarioCanvas()
      syncHandlesFnRef.current()
    })
    ro.observe(mainRef.current)
    ro.observe(rsiRef.current)
    syncScenarioCanvas()   // 초기 크기 설정

    return () => {
      ro.disconnect()
      main.remove()
      rsiChart.remove()
      chartRef.current = { main: null, rsi: null }
      s.current = null
    }
  }, [])

  // ── keep refs current + redraw + sync handles ──
  useEffect(() => {
    scenarioRef.current = scenario
    drawFnRef.current()
    syncHandlesFnRef.current()
  }, [scenario])

  useEffect(() => { isOverseasRef.current = !/^\d+$/.test(symbol) }, [symbol])
  useEffect(() => { symbolRef.current = symbol }, [symbol])
  useEffect(() => { drawnLinesRef.current = drawnLines; drawFnRef.current() }, [drawnLines])
  useEffect(() => { drawFnRef.current() }, [livePrices[symbol]])

  useEffect(() => {
    if (!selectedTradeId || !data?.length) {
      tradeScenarioRef.current = null
      drawFnRef.current()
      return
    }
    const trades = queryClient.getQueryData<JournalTrade[]>(['journal', userId])
    const trade = trades?.find(t => String(t.id) === String(selectedTradeId))
    if (!trade) { tradeScenarioRef.current = null; drawFnRef.current(); return }
    const barIndex = data.findIndex(b => (b.Date as string) === trade.date)
    if (barIndex < 0) { tradeScenarioRef.current = null; drawFnRef.current(); return }
    tradeScenarioRef.current = { trade, tradeBarIndex: barIndex, startPrice: data[barIndex].Close }
    drawFnRef.current()
  }, [selectedTradeId, data, userId]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setDrawingMode('none') }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  const onCrosshairBtnClick = useCallback(() => {
    const price = crosshairPriceRef.current
    if (price == null) return
    const snapped = isOverseasRef.current ? +price.toFixed(2) : Math.round(price)
    addDrawnLine(symbolRef.current, { id: `h-${Date.now()}`, type: 'horizontal', color: '#e2e8f0', price: snapped })
  }, [addDrawnLine])

  const onChartMouseMove = useCallback((e: React.MouseEvent) => {
    const btn = crosshairBtnRef.current
    const ser = s.current
    if (!btn || !ser || !mainRef.current) return
    const rect = mainRef.current.getBoundingClientRect()
    const y = e.clientY - rect.top
    const price = ser.candle.coordinateToPrice(y) as number | null
    crosshairPriceRef.current = price
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const scaleW = (chartRef.current.main?.priceScale('right') as any)?.width?.() ?? 65
    btn.style.top     = `${y}px`
    btn.style.right   = `${scaleW}px`
    btn.style.display = 'flex'
  }, [])

  const onDrawMouseDown = useCallback((e: React.MouseEvent) => {
    const main = chartRef.current.main
    const ser  = s.current
    if (!main || !ser || !mainRef.current) return
    const rect = mainRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    if (drawingModeRef.current === 'segment') {
      const logical = main.timeScale().coordinateToLogical(x) as number | null
      const price   = ser.candle.coordinateToPrice(y) as number | null
      if (logical == null || price == null) return
      const snapped = isOverseasRef.current ? +price.toFixed(2) : Math.round(price)
      segmentStartRef.current = { barOffset: logical - (dataLengthRef.current - 1), price: snapped, px: x, py: y }
      isDrawingRef.current = true
    }
  }, [addDrawnLine])

  const onDrawMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDrawingRef.current || !segmentStartRef.current || !mainRef.current) return
    const rect = mainRef.current.getBoundingClientRect()
    drawTempRef.current = { x1: segmentStartRef.current.px, y1: segmentStartRef.current.py, x2: e.clientX - rect.left, y2: e.clientY - rect.top }
    drawFnRef.current()
  }, [])

  const onDrawMouseUp = useCallback((e: React.MouseEvent) => {
    if (!isDrawingRef.current || !segmentStartRef.current) return
    isDrawingRef.current = false
    drawTempRef.current  = null
    const main = chartRef.current.main
    const ser  = s.current
    if (!main || !ser || !mainRef.current) { segmentStartRef.current = null; return }
    const rect    = mainRef.current.getBoundingClientRect()
    const x       = e.clientX - rect.left
    const y       = e.clientY - rect.top
    const logical = main.timeScale().coordinateToLogical(x) as number | null
    const price   = ser.candle.coordinateToPrice(y) as number | null
    if (logical == null || price == null) { segmentStartRef.current = null; return }
    const snapped = isOverseasRef.current ? +price.toFixed(2) : Math.round(price)
    const start   = segmentStartRef.current
    addDrawnLine(symbolRef.current, {
      id: `s-${Date.now()}`, type: 'segment', color: '#e2e8f0',
      barOffset1: start.barOffset, price1: start.price,
      barOffset2: logical - (dataLengthRef.current - 1), price2: snapped,
    })
    segmentStartRef.current = null
  }, [addDrawnLine])

  const onDrawContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    const main = chartRef.current.main
    const ser  = s.current
    if (!main || !ser || !mainRef.current) return
    const rect = mainRef.current.getBoundingClientRect()
    const cx   = e.clientX - rect.left
    const cy   = e.clientY - rect.top
    const THRESH = 8
    const lines = drawnLinesRef.current[symbolRef.current] ?? []
    for (const line of lines) {
      if (line.type === 'horizontal' && line.price != null) {
        const ly = ser.candle.priceToCoordinate(line.price) as number | null
        if (ly != null && Math.abs(ly - cy) < THRESH) { removeDrawnLine(symbolRef.current, line.id); return }
      } else if (line.type === 'segment' && line.barOffset1 != null && line.price1 != null && line.barOffset2 != null && line.price2 != null) {
        const ts = main.timeScale()
        const ll = dataLengthRef.current - 1
        const x1 = ts.logicalToCoordinate((ll + line.barOffset1) as unknown as Logical) as number | null
        const y1 = ser.candle.priceToCoordinate(line.price1) as number | null
        const x2 = ts.logicalToCoordinate((ll + line.barOffset2) as unknown as Logical) as number | null
        const y2 = ser.candle.priceToCoordinate(line.price2) as number | null
        if (x1 != null && y1 != null && x2 != null && y2 != null && distToSegment(cx, cy, x1, y1, x2, y2) < THRESH) {
          removeDrawnLine(symbolRef.current, line.id); return
        }
      }
    }
  }, [removeDrawnLine])

  // ── update data ──
  useEffect(() => {
    if (!s.current || !data?.length) return
    dataLengthRef.current = data.length
    const { candle, volume, mas, rsi, rsi70, rsi30 } = s.current

    const times  = data.map(b => b.Date as string)
    const closes = data.map(b => b.Close)

    candle.setData(data.map(b => ({
      time: b.Date as string,
      open: b.Open, high: b.High, low: b.Low, close: b.Close,
    })))

    volume.setData(data.map(b => ({
      time: b.Date as string,
      value: b.Volume,
      color: b.Close >= b.Open ? 'rgba(239,83,80,0.5)' : 'rgba(33,150,243,0.5)',
    })))

    for (const p of MA_PERIODS) {
      const vals = calcMa(closes, p)
      mas[p].setData(
        vals.flatMap((v, i) => v !== null ? [{ time: times[i], value: v }] : [])
      )
    }

    const rsiVals = calcRsi(closes)
    rsi.setData(rsiVals.flatMap((v, i) => v !== null ? [{ time: times[i], value: +v.toFixed(2) }] : []))
    rsi70.setData(times.map(t => ({ time: t, value: 70 })))
    rsi30.setData(times.map(t => ({ time: t, value: 30 })))

    chartRef.current.main?.timeScale().fitContent()

    if (data.length >= 2) {
      setPrevClose(symbol, data.at(-2)!.Close)
    }
  }, [data]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── MA toggle ──
  useEffect(() => {
    if (!s.current) return
    for (const p of MA_PERIODS) s.current.mas[p]?.applyOptions({ visible: showMa })
  }, [showMa])

  // ── 시나리오 price lines (LW-charts, display only) ──
  useEffect(() => {
    const ser = s.current
    if (!ser || !scenario) return

    const create = (price: number, color: string, style: number, title: string) =>
      ser.candle.createPriceLine({ price, color, lineWidth: 1, lineStyle: style, axisLabelVisible: true, title, draggable: false })

    const pl: Record<string, ReturnType<typeof create>> = {}
    pl.resist = create(scenario.resistPrice, '#e2e8f0', 0, '저항')
    if (scenario.supportPrice) pl.support = create(scenario.supportPrice, '#94a3b8', 0, '지지')
    pl.target = create(scenario.targetPrice, '#2ecc71', 1, '목표')
    pl.sl     = create(scenario.stopLoss,    '#ef4444', 1, '손절')
    scenarioPLinesRef.current = pl

    return () => {
      for (const line of Object.values(pl)) {
        try { ser.candle.removePriceLine(line) } catch {}
      }
      scenarioPLinesRef.current = {}
    }
  }, [scenario])

  const { isInWatchlist, toggle } = useWatchlist()
  const isOverseas = !symbol.match(/^\d+$/)

  const startDrag = (type: 'resist' | 'support') => (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const hRef = type === 'resist' ? resistHandleRef : supportHandleRef

    const onMove = (ev: MouseEvent) => {
      const rect = mainRef.current?.getBoundingClientRect()
      if (!rect || !hRef.current) return
      const y   = Math.max(0, Math.min(ev.clientY - rect.top, rect.height))
      const raw = s.current?.candle.coordinateToPrice(y) as number | null
      hRef.current.style.top = `${y}px`
      if (raw != null) {
        const line = scenarioPLinesRef.current[type === 'resist' ? 'resist' : 'support']
        line?.applyOptions({ price: raw })
      }
    }

    const onUp = (ev: MouseEvent) => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      const rect = mainRef.current?.getBoundingClientRect()
      if (!rect) return
      const y = Math.max(0, Math.min(ev.clientY - rect.top, rect.height))
      const raw = s.current?.candle.coordinateToPrice(y) as number | null
      if (raw == null) return
      const price = isOverseasRef.current ? +raw.toFixed(2) : Math.round(raw / 10) * 10
      setScenarioDrag(type === 'resist' ? { resistPrice: price } : { supportPrice: price })
    }

    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }
  const isStarred = isInWatchlist(symbol)

  const livePrice    = livePrices[symbol]
  const displayPrice = livePrice ?? data?.at(-1)?.Close
  const prevClose    = prevCloses[symbol]
  displayPriceRef.current = displayPrice ?? null

  const priceLabel = displayPrice != null
    ? (isOverseas ? `$${displayPrice.toFixed(2)}` : `${displayPrice.toLocaleString()}원`)
    : ''

  const changePct = displayPrice != null && prevClose != null && prevClose > 0
    ? ((displayPrice - prevClose) / prevClose) * 100
    : null

  return (
    <div className="chart-view">
      {/* toolbar */}
      <div className="chart-toolbar">
        <StockSearch />
        <span className="symbol-label">
          {symbolName} <span className="symbol-code">({symbol})</span>
        </span>
        <button
          className={`chart-star-btn ${isStarred ? 'starred' : ''}`}
          onClick={() => toggle(symbol, symbolName)}
          title={isStarred ? '관심종목 제거' : '관심종목 추가'}
        >
          {isStarred ? '⭐' : '☆'}
        </button>
        {priceLabel && (
          <span className="current-price-wrap">
            <span className="current-price">{priceLabel}</span>
            {changePct != null && (
              <span className={`current-change ${changePct >= 0 ? 'up' : 'down'}`}>
                {changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%
              </span>
            )}
          </span>
        )}
        {isLoading && <span className="chart-loading">로딩 중...</span>}

        <div className="toolbar-right">
          <label className="toggle-label">
            <input type="checkbox" checked={showMa} onChange={e => setShowMa(e.target.checked)} />
            MA
          </label>
          <label className="toggle-label">
            <input type="checkbox" checked={showRsi} onChange={e => setShowRsi(e.target.checked)} />
            RSI
          </label>
          <div className="draw-buttons">
            <button
              className={`draw-btn ${drawingMode === 'segment' ? 'active' : ''}`}
              onClick={() => setDrawingMode(drawingMode === 'segment' ? 'none' : 'segment')}
              title="선분 (Esc 종료)"
            >╱</button>
            {(drawnLines[symbol]?.length ?? 0) > 0 && (
              <button
                className="draw-btn draw-btn-clear"
                onClick={() => clearDrawnLines(symbol)}
                title="선 모두 삭제"
              >✕</button>
            )}
          </div>
          <div className="period-buttons">
            {(['D', 'W'] as Period[]).map(p => (
              <button
                key={p}
                className={`period-btn ${period === p ? 'active' : ''}`}
                onClick={() => setPeriod(p)}
              >
                {p === 'D' ? '일' : '주'}
              </button>
            ))}
          </div>
          <select
            className="count-select"
            value={count}
            onChange={e => setCount(+e.target.value)}
          >
            <option value={200}>200</option>
            <option value={500}>500</option>
            <option value={900}>900</option>
            <option value={1500}>1500</option>
          </select>
        </div>
      </div>

      {/* main chart + scenario overlay */}
      <div
        className="chart-wrap"
        onMouseMove={onChartMouseMove}
        onMouseLeave={() => {
          if (crosshairBtnRef.current) crosshairBtnRef.current.style.display = 'none'
        }}
      >
        <div ref={mainRef} className="chart-container" />
        <canvas ref={scenarioCanvasRef} className="scenario-canvas" />
        <div ref={resistHandleRef}  className="drag-handle" style={{ display: 'none' }} onMouseDown={startDrag('resist')} />
        <div ref={supportHandleRef} className="drag-handle" style={{ display: 'none' }} onMouseDown={startDrag('support')} />
        <div
          ref={crosshairBtnRef}
          className="crosshair-add-btn"
          onClick={onCrosshairBtnClick}
          title="수평선 추가"
        >+</div>
        {drawingMode !== 'none' && (
          <div
            className="draw-overlay"
            onMouseDown={onDrawMouseDown}
            onMouseMove={onDrawMouseMove}
            onMouseUp={onDrawMouseUp}
            onContextMenu={onDrawContextMenu}
          />
        )}
      </div>

      {/* RSI sub-chart */}
      <div
        ref={rsiRef}
        className="rsi-container"
        style={{ flex: showRsi ? '0 0 82px' : '0 0 0px', overflow: 'hidden' }}
      />
    </div>
  )
}
