import { useState, useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChartView } from './components/chart/ChartView'
import { Watchlist } from './components/watchlist/Watchlist'
import { Calculator } from './components/calculator/Calculator'
import { TradeJournal } from './components/journal/TradeJournal'
import { useAppStore } from './store'
import './App.css'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000 } },
})

function AppInner() {
  const { userId, setUserId } = useAppStore()
  const [codeInput, setCodeInput] = useState('')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const u = params.get('u')
    if (u) {
      setUserId(u)
      // URL에서 파라미터 제거 (히스토리 오염 방지)
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [setUserId])

  if (!userId) {
    return (
      <div className="access-gate">
        <div className="access-gate-box">
          <div className="access-gate-title">접속 코드를 입력하세요</div>
          <input
            className="access-gate-input"
            type="text"
            placeholder="코드 입력"
            value={codeInput}
            onChange={e => setCodeInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && codeInput.trim() && setUserId(codeInput.trim())}
          />
          <button
            className="access-gate-btn"
            onClick={() => codeInput.trim() && setUserId(codeInput.trim())}
          >
            입장
          </button>
        </div>
      </div>
    )
  }

  return <AppContent />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  )
}

function AppContent() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [sidebarW, setSidebarW] = useState(210)
  const [calcOpen, setCalcOpen] = useState(true)
  const [calcW, setCalcW] = useState(320)
  const { sidebarTab, rightTab, setRightTab } = useAppStore()

  // MY 탭 선택 시 사이드바 자동 확장
  useEffect(() => {
    if (sidebarTab === 'my') {
      setSidebarOpen(true)
      setSidebarW(w => Math.max(w, 360))
    }
  }, [sidebarTab])

  // 드래그 리사이즈 팩토리 (마우스 + 터치 공통)
  const startDrag = (
    axis: 'x' | 'y',
    initVal: number,
    set: (v: number) => void,
    min: number,
    max: number,
    inv = false,
  ) => (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault()
    const getPos = (ev: MouseEvent | TouchEvent) =>
      'touches' in ev
        ? (axis === 'x' ? ev.touches[0].clientX : ev.touches[0].clientY)
        : (axis === 'x' ? ev.clientX : ev.clientY)
    const origin = 'touches' in e.nativeEvent
      ? (axis === 'x' ? (e as React.TouchEvent).touches[0].clientX : (e as React.TouchEvent).touches[0].clientY)
      : (axis === 'x' ? (e as React.MouseEvent).clientX : (e as React.MouseEvent).clientY)
    const onMove = (ev: MouseEvent | TouchEvent) => {
      const d = getPos(ev) - origin
      set(Math.max(min, Math.min(max, initVal + (inv ? -d : d))))
    }
    const onUp = () => {
      document.removeEventListener('mousemove', onMove as EventListener)
      document.removeEventListener('mouseup', onUp)
      document.removeEventListener('touchmove', onMove as EventListener)
      document.removeEventListener('touchend', onUp)
    }
    document.addEventListener('mousemove', onMove as EventListener)
    document.addEventListener('mouseup', onUp)
    document.addEventListener('touchmove', onMove as EventListener, { passive: false })
    document.addEventListener('touchend', onUp)
  }

  return (
    <div className="app">

      {/* 헤더 */}
        <header className="app-header">
          <span className="app-logo"> 이란 매매법 </span>
        </header>

        <div className="app-body">

          {/* 사이드바 */}
          <div className="sidebar-wrap" style={{ width: sidebarOpen ? sidebarW : 0 }}>
            <aside className="sidebar">
              <Watchlist />
            </aside>
          </div>

          {/* 사이드바 분할선 + 토글 */}
          <div
            className="divider-v"
            style={{ cursor: sidebarOpen ? 'ew-resize' : 'default' }}
            onMouseDown={sidebarOpen ? startDrag('x', sidebarW, setSidebarW, 140, 420) : undefined}
            onTouchStart={sidebarOpen ? startDrag('x', sidebarW, setSidebarW, 140, 420) : undefined}
          >
            <button
              className="panel-toggle-btn"
              onClick={e => { e.stopPropagation(); setSidebarOpen(o => !o) }}
            >
              {sidebarOpen ? '‹' : '›'}
            </button>
          </div>

          <div className="content">
            <div className="top-row">
              <div className="chart-col">
                <ChartView />
              </div>

              {/* 차트-계산기 분할선 */}
              <div
                className="divider-v divider-v-calc"
                style={{ cursor: calcOpen ? 'ew-resize' : 'default' }}
                onMouseDown={calcOpen ? startDrag('x', calcW, setCalcW, 220, 500, true) : undefined}
                onTouchStart={calcOpen ? startDrag('x', calcW, setCalcW, 220, 500, true) : undefined}
              >
                <button
                  className="panel-toggle-btn panel-toggle-inline"
                  onClick={e => { e.stopPropagation(); setCalcOpen(o => !o) }}
                >
                  {calcOpen ? '›' : '‹'}
                </button>
              </div>

              <div className="calc-col" style={{ width: calcOpen ? calcW : 0 }}>
                {/* 우측 패널 탭 */}
                <div className="right-panel-tabs">
                  <button
                    className={`right-panel-tab ${rightTab === 'calc' ? 'active' : ''}`}
                    onClick={() => setRightTab('calc')}
                  >계산기</button>
                  <button
                    className={`right-panel-tab ${rightTab === 'journal' ? 'active' : ''}`}
                    onClick={() => setRightTab('journal')}
                  >일지</button>
                </div>
                <div className="right-panel-content">
                  <div style={{ display: rightTab === 'calc' ? 'block' : 'none', height: '100%', overflowY: 'auto', padding: '10px 12px' }}>
                    <Calculator />
                  </div>
                  <div style={{ display: rightTab === 'journal' ? 'flex' : 'none', flexDirection: 'column', height: '100%' }}>
                    <TradeJournal />
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>{/* app-body */}
      </div>
  )
}
