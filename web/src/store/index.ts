import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Period, ScenarioData, DrawnLine, SidebarTab } from '../types'

interface AppState {
  // auth
  userId: string | null
  setUserId: (id: string) => void

  // sidebar tab (not persisted)
  sidebarTab: SidebarTab
  setSidebarTab: (tab: SidebarTab) => void

  // chart
  symbol: string
  symbolName: string
  period: Period

  // calculator shared
  totalAsset: number
  riskPct: number

  // scenario overlay (canvas drawing)
  scenario: ScenarioData | null

  // price line drag feedback (ChartView → StrategyTab)
  scenarioDrag: { resistPrice?: number; supportPrice?: number } | null

  // user-drawn lines (persisted per symbol)
  drawnLines: Record<string, DrawnLine[]>

  // live prices (websocket)
  livePrices: Record<string, number>

  // previous close prices (for 등락률)
  prevCloses: Record<string, number>

  // actions
  setSymbol: (symbol: string, name?: string) => void
  setPeriod: (period: Period) => void
  setTotalAsset: (v: number) => void
  setRiskPct: (v: number) => void
  setScenario: (s: ScenarioData | null) => void
  setScenarioDrag: (v: { resistPrice?: number; supportPrice?: number } | null) => void
  addDrawnLine: (symbol: string, line: DrawnLine) => void
  removeDrawnLine: (symbol: string, id: string) => void
  clearDrawnLines: (symbol: string) => void
  setLivePrice: (symbol: string, price: number) => void
  setPrevClose: (symbol: string, price: number) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      userId: null,
      sidebarTab: 'watchlist',
      symbol: '005930',
      symbolName: '삼성전자',
      period: 'D',
      totalAsset: 50_000_000,
      riskPct: 0.4,
      scenario: null,
      scenarioDrag: null,
      drawnLines: {},
      livePrices: {},
      prevCloses: {},

      setUserId: (id) => set({ userId: id }),
      setSidebarTab: (tab) => set({ sidebarTab: tab }),
      setSymbol: (symbol, name) => set({ symbol, symbolName: name ?? symbol }),
      setPeriod: (period) => set({ period }),
      setTotalAsset: (v) => set({ totalAsset: v }),
      setRiskPct: (v) => set({ riskPct: v }),
      setScenario: (scenario) => set({ scenario }),
      setScenarioDrag: (scenarioDrag) => set({ scenarioDrag }),
      addDrawnLine: (symbol, line) =>
        set((s) => ({ drawnLines: { ...s.drawnLines, [symbol]: [...(s.drawnLines[symbol] ?? []), line] } })),
      removeDrawnLine: (symbol, id) =>
        set((s) => ({ drawnLines: { ...s.drawnLines, [symbol]: (s.drawnLines[symbol] ?? []).filter(l => l.id !== id) } })),
      clearDrawnLines: (symbol) =>
        set((s) => ({ drawnLines: { ...s.drawnLines, [symbol]: [] } })),
      setLivePrice: (symbol, price) =>
        set((s) => ({ livePrices: { ...s.livePrices, [symbol]: price } })),
      setPrevClose: (symbol, price) =>
        set((s) => ({ prevCloses: { ...s.prevCloses, [symbol]: price } })),
    }),
    {
      name: 'stocks-app',
      partialize: (s) => ({
        userId: s.userId,
        symbol: s.symbol,
        symbolName: s.symbolName,
        period: s.period,
        totalAsset: s.totalAsset,
        riskPct: s.riskPct,
        drawnLines: s.drawnLines,
      }),
    }
  )
)
