# React 이전 계획

Streamlit 버전은 유지하면서 React + FastAPI 구조로 새 프로젝트를 병행 개발한다.

---

## 전체 아키텍처

```
┌─────────────────────────────────┐     ┌──────────────────────────────┐
│         React Frontend          │     │       FastAPI Backend         │
│  (Vite + TypeScript)            │     │       (Python 유지)           │
│                                 │     │                               │
│  <App />                        │     │  /api/ohlcv                   │
│  ├── <Sidebar />                │◀────│  /api/stock-info              │
│  ├── <Chart />                  │ REST│  /api/stock-search            │
│  ├── <SettingsPanel />          │     │  /api/price                   │
│  ├── <TradeJournal />           │     │  /api/order  (KIS)            │
│  ├── <OrderPanel />             │     │  /api/account (KIS)           │
│  └── <AccountPanel />           │◀────│  /ws/price   (KIS → 브라우저) │
│                                 │  WS │                               │
│  Supabase JS ───────────────────┼─────┼──▶ Supabase (직접)           │
└─────────────────────────────────┘     └──────────────────────────────┘
```

### 분리 기준

| 유지 (FastAPI) | 이전 (React/TS) |
|---------------|----------------|
| `data_loader.py` — FinanceDataReader Python 전용 | 모든 UI 컴포넌트 |
| `kis_websocket.py` — KIS 실시간 WebSocket 클라이언트 | 전략 계산 로직 (TS 포팅) |
| `kis_client.py` — KIS REST API / 인증·시크릿 | Supabase 직접 호출 |
| `calculator.py` — API endpoint로 노출 또는 TS 포팅 | 차트 렌더링 |

---

## 추천 기술 스택

```
React 18 + Vite + TypeScript
Tailwind CSS                  — 레이아웃, 다크 테마
Zustand                       — 전역 상태 (현재가, 선택 종목 등)
TanStack Query                — API 캐싱 (st.cache_data 대체)
lightweight-charts            — 캔들 차트 (현재와 동일 엔진)
AG Grid Community             — 매매 일지 테이블 (st.data_editor 대체)
Radix UI                      — 탭, 셀렉트, 체크박스 등 헤드리스 컴포넌트
@supabase/supabase-js         — DB 직접 연동
FastAPI + uvicorn             — Python 백엔드
```

---

## 파일 구조

```
stocks-react/
├── src/
│   ├── app/
│   │   └── App.tsx                  # 루트 레이아웃
│   ├── components/
│   │   ├── chart/
│   │   │   ├── Chart.tsx            # Lightweight Charts 래퍼
│   │   │   ├── useChartLines.ts     # 전략선 추가 훅
│   │   │   └── useScenario.ts       # 시나리오 드로잉 훅
│   │   ├── settings/
│   │   │   ├── SettingsPanel.tsx    # 전략 계산기 루트
│   │   │   ├── BreakoutTab.tsx      # 손잡이컵 탭
│   │   │   ├── ReversalTab.tsx      # 역추세 탭
│   │   │   ├── BlueChipTab.tsx      # 우량주 탭
│   │   │   └── SidewaysTab.tsx      # 횡보돌파 탭
│   │   ├── journal/
│   │   │   ├── TradeJournal.tsx     # 일지 루트
│   │   │   ├── JournalTable.tsx     # AG Grid 테이블
│   │   │   ├── JournalForm.tsx      # 새 일지 폼
│   │   │   └── SummaryCard.tsx      # 승률/손익비 요약
│   │   ├── order/
│   │   │   ├── OrderPanel.tsx       # 주문창 루트
│   │   │   ├── OrderInput.tsx       # 일반/자동 주문 입력
│   │   │   └── OrderStatus.tsx      # 감시 주문 목록
│   │   ├── account/
│   │   │   └── AccountPanel.tsx     # 계좌 잔고/보유
│   │   └── sidebar/
│   │       ├── Sidebar.tsx          # 사이드바 루트
│   │       └── Watchlist.tsx        # 관심 종목
│   ├── hooks/
│   │   ├── useRealtimePrice.ts      # WebSocket 현재가
│   │   ├── useOhlcv.ts              # OHLCV TanStack Query
│   │   └── useStockInfo.ts          # 종목 정보 TanStack Query
│   ├── store/
│   │   └── useAppStore.ts           # Zustand 전역 상태
│   ├── lib/
│   │   ├── calculator.ts            # calculator.py → TS 포팅
│   │   ├── supabase.ts              # Supabase 클라이언트
│   │   └── api.ts                   # FastAPI 호출 유틸
│   └── types/
│       └── index.ts                 # 공통 타입 정의
│
└── api/                             # FastAPI 백엔드
    ├── main.py
    ├── routers/
    │   ├── stock.py                 # /api/ohlcv, /api/stock-info
    │   ├── order.py                 # /api/order (KIS)
    │   └── account.py              # /api/account (KIS)
    └── ws/
        └── price.py                 # /ws/price (KIS → 브라우저)
```

---

## 컴포넌트별 상세 계획

### 1. `<Chart />`

**현재**: `components/chart.py` → `renderLightweightCharts(charts, key='chart_v2')`

**React 구현**:
```tsx
// Chart.tsx
import { createChart, IChartApi } from 'lightweight-charts'

const Chart = ({ ohlcv, lines, rsiEnabled, maOptions }: ChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    chartRef.current = createChart(containerRef.current!, {
      height: 500,
      layout: { background: { color: '#131722' }, textColor: '#d1d4dc' },
      ...
    })
    // candleSeries, volumeSeries, maSeries 추가
  }, [])

  // 전략선 업데이트 (저항선, 손절, 목표가 등)
  useChartLines(chartRef, lines)

  return <div ref={containerRef} />
}
```

**핵심 포인트**:
- 현재 Python에서 생성하는 `series` JSON 구조가 JS API와 거의 동일 → 변환 비용 낮음
- RSI 서브차트: `createChart` 두 번 호출로 동기화
- MA: 프론트에서 직접 계산 (`close.map(...)` 롤링 평균)

---

### 2. `<SettingsPanel />` — 전략 계산기

**현재**: `components/settings_panel.py` → `_breakout_tab()` 헬퍼 + 4개 탭

**React 구현**:

```tsx
// SettingsPanel.tsx
const SettingsPanel = ({ currentPrice, symbol }: Props) => {
  return (
    <Tabs defaultValue="breakout">
      <TabsList>
        <TabsTrigger value="breakout">🏺 손잡이컵</TabsTrigger>
        <TabsTrigger value="reversal">📉 역추세</TabsTrigger>
        <TabsTrigger value="bluechip">🏦 우량주</TabsTrigger>
        <TabsTrigger value="sideways">🔄 횡보돌파</TabsTrigger>
      </TabsList>
      <TabsContent value="breakout">
        <BreakoutTab config={{ slPct: 4, missedSlPct: 5, rrMultiple: 4, missedLogic: 'pullback' }} />
      </TabsContent>
      ...
    </Tabs>
  )
}
```

```tsx
// BreakoutTab.tsx — _breakout_tab() 대응
const BreakoutTab = ({ config }: Props) => {
  const [resistPrice, setResistPrice] = useState(0)
  const [supportPrice, setSupportPrice] = useState(0)
  const [missed, setMissed] = useState(false)

  // calculator.ts의 순수 함수 호출
  const result = useMemo(() =>
    calcBreakout({ resistPrice, supportPrice, missed, ...config }),
    [resistPrice, supportPrice, missed]
  )

  return (
    <>
      <Checkbox checked={missed} onChange={setMissed}>돌파 놓침</Checkbox>
      <NumberInput label="저항선" value={resistPrice} onChange={setResistPrice} />
      {isZoneMode && <NumberInput label="지지선" value={supportPrice} onChange={setSupportPrice} />}
      <StrategyResult result={result} />
    </>
  )
}
```

**`calculator.ts`** (calculator.py → TS 포팅):
```ts
export function calcBreakout({ resistPrice, supportPrice, missed, slPct, missedSlPct, rrMultiple, budget }) {
  // Python 로직 그대로 이식
  const isZone = missed && supportPrice > 0
  const prices = isZone
    ? [resistPrice - rng/3, resistPrice - rng*2/3, supportPrice]
    : missed
      ? [resistPrice * 1.04, resistPrice * 1.01, resistPrice * 0.98]
      : [resistPrice * 1.02, resistPrice * 0.98]
  ...
  return { prices, avgPrice, hardSl, target, allocations }
}
```

---

### 3. `<TradeJournal />` — 매매 일지

**현재**: `components/trade_journal.py` → `st.data_editor` + 새 일지 폼

**React 구현**:

```tsx
// JournalTable.tsx — st.data_editor 대체
import { AgGridReact } from 'ag-grid-react'

const JournalTable = () => {
  const { data, refetch } = useQuery({ queryKey: ['trades'], queryFn: fetchTrades })

  const onCellValueChanged = async (event: CellValueChangedEvent) => {
    await supabase.from('trades').update(event.data).eq('id', event.data.id)
    refetch()
  }

  const columnDefs: ColDef[] = [
    { field: 'result', editable: true, cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: ['수익', '손절', '보유', '감시'] } },
    { field: 'ticker', editable: true },
    { field: 'pattern', editable: true, cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: PATTERNS } },
    { field: 'avg_price', editable: false, valueGetter: calcAvgPrice },
    { field: 'profit_rate', editable: false, valueGetter: calcProfitRate },
    ...
  ]

  return <AgGridReact rowData={data} columnDefs={columnDefs} onCellValueChanged={onCellValueChanged} />
}
```

```tsx
// JournalForm.tsx — _render_new_journal_form() 대응
const JournalForm = () => {
  const [pattern, setPattern] = useState('손잡이컵')
  const [resistPrice, setResistPrice] = useState(0)

  // 저항선 변경 시 자동계산 (현재 nj_autofill_prev 로직 대응)
  const autoFill = useMemo(() => calcAutoFill(pattern, resistPrice, supportPrice), [pattern, resistPrice, supportPrice])

  const onSubmit = async () => {
    await supabase.from('trades').insert(payload)
  }
  ...
}
```

**파생 컬럼** (`FRONTEND_COMPUTED`): AG Grid `valueGetter`로 동일하게 런타임 계산

---

### 4. `<Sidebar />` + `<Watchlist />`

**현재**: `components/sidebar.py` → 관심 종목 목록 + 종목 검색 + 현재가 병렬 조회

**React 구현**:

```tsx
// useRealtimePrice.ts — GLOBAL_PRICES 대응
const useRealtimePrice = (symbols: string[]) => {
  const [prices, setPrices] = useState<Record<string, number>>({})

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/price')
    ws.onmessage = (e) => {
      const { code, price } = JSON.parse(e.data)
      setPrices(prev => ({ ...prev, [code]: price }))
    }
    return () => ws.close()
  }, [])

  return prices
}

// Watchlist.tsx
const Watchlist = () => {
  const { data: watchlist } = useQuery({ queryKey: ['watchlist'], queryFn: fetchWatchlist })
  const prices = useRealtimePrice(watchlist?.map(w => w.stock_code) ?? [])

  return watchlist?.map(stock => (
    <WatchlistItem key={stock.stock_code} stock={stock} price={prices[stock.stock_code]} />
  ))
}
```

**FastAPI WebSocket** (`/ws/price`):
```python
# ws/price.py
@app.websocket("/ws/price")
async def price_ws(websocket: WebSocket):
    await websocket.accept()
    # KIS WebSocket에서 받은 데이터를 브라우저로 중계
    async def callback(code, price):
        await websocket.send_json({"code": code, "price": price})
    await kis_ws.receive_loop(callback)
```

---

### 5. `<OrderPanel />`

**현재**: `components/order_panel.py` → 일반 주문 / 자동 매수 / 자동 매도 탭 + 감시 주문 목록

**React 구현**:
- 탭: Radix UI Tabs
- 주문 입력: 제어 컴포넌트 (`useState`)
- 주문 전송: `POST /api/order` → FastAPI → KIS REST
- 감시 주문: Supabase `watch_orders` 테이블 직접 구독 (`supabase.channel().on('postgres_changes', ...)`)

```tsx
// 감시 주문 실시간 구독 — Supabase Realtime
useEffect(() => {
  const channel = supabase.channel('watch_orders')
    .on('postgres_changes', { event: '*', schema: 'public', table: 'watch_orders' },
      () => refetch()
    ).subscribe()
  return () => supabase.removeChannel(channel)
}, [])
```

---

### 6. `<AccountPanel />`

**현재**: `components/account_panel.py` → KIS API로 잔고 조회

**React 구현**:
```tsx
const { data: account } = useQuery({
  queryKey: ['account', accIdx],
  queryFn: () => fetch(`/api/account?acc=${accIdx}`).then(r => r.json()),
  refetchInterval: 30_000  // 30초 폴링 (st.cache_data ttl=30 대응)
})
```

---

### 7. `<ScenarioDrawing />` — 신규 기능

**현재**: 없음 (Streamlit에서 구현 불가)

**React 구현**:
```ts
// useScenario.ts
const useScenario = (chart: IChartApi, series: ISeriesApi) => {
  const [points, setPoints] = useState<ScenarioPoint[]>([])

  const enableDrawing = () => {
    chart.subscribeClick((param) => {
      const price = series.coordinateToPrice(param.point.y)
      const time  = chart.timeScale().coordinateToTime(param.point.x)
      setPoints(prev => [...prev, { time, price }])
    })
  }

  // points 배열 → LineSeries로 W자·화살표 렌더
  useEffect(() => {
    if (points.length < 2) return
    scenarioSeries.setData(points)
  }, [points])

  return { enableDrawing, clearScenario: () => setPoints([]) }
}
```

**지원 시나리오 유형**:
- 자유선 (클릭으로 꺾임점 배치)
- W자 프리셋 (현재가 기준 자동 배치)
- 화살표 (Primitives API)

---

## 전역 상태 (`useAppStore.ts`)

```ts
// Zustand — st.session_state 대응
interface AppStore {
  symbol: string
  symbolName: string
  isOverseas: boolean
  currentPrice: number
  wsStatus: string

  setSymbol: (s: string) => void
  setCurrentPrice: (p: number) => void
}

export const useAppStore = create<AppStore>((set) => ({
  symbol: '005930',
  symbolName: '삼성전자',
  isOverseas: false,
  currentPrice: 0,
  wsStatus: '연결 대기 중',
  setSymbol: (symbol) => set({ symbol }),
  setCurrentPrice: (currentPrice) => set({ currentPrice }),
}))
```

---

## FastAPI 엔드포인트 목록

```
GET  /api/ohlcv?symbol=&count=&period=    — data_loader.get_ohlcv
GET  /api/stock-info?q=                   — data_loader.get_stock_info
GET  /api/stock-search?q=                 — data_loader.search_stock_naver
GET  /api/price?symbol=                   — data_loader.get_current_price
GET  /api/account?acc=                    — kis_client 잔고 조회
POST /api/order                           — kis_client 주문 전송
WS   /ws/price                            — KIS WebSocket → 브라우저 중계
```

---

## Streamlit → React 대응표

| Streamlit | React |
|-----------|-------|
| `st.session_state` | Zustand store |
| `st.cache_data(ttl=N)` | TanStack Query `staleTime` |
| `st.columns([7,3])` | CSS Grid `grid-cols-[7fr_3fr]` |
| `st.tabs` | Radix UI Tabs |
| `st.number_input` | `<input type="number">` + 제어 컴포넌트 |
| `st.selectbox` | Radix UI Select |
| `st.checkbox` | Radix UI Checkbox |
| `st.pills` | Radix UI ToggleGroup |
| `st.data_editor` | AG Grid Community (인라인 편집) |
| `st.rerun()` | 상태 업데이트 → 자동 리렌더 |
| `st.dialog` | Radix UI Dialog |
| `st.container(border=True)` | Tailwind `border rounded-lg p-4` |
| `renderLightweightCharts` | `lightweight-charts` npm 직접 |

---

## 이전 우선순위

```
1단계 — 기반
  ├── FastAPI 서버 + /api/ohlcv, /api/stock-info 엔드포인트
  ├── /ws/price WebSocket 중계
  └── <Chart /> Lightweight Charts 기본 렌더

2단계 — 핵심 기능
  ├── <SettingsPanel /> + calculator.ts 포팅
  ├── Zustand store (symbol, price, wsStatus)
  └── <Sidebar /> + <Watchlist /> + 실시간 가격

3단계 — 데이터
  ├── <TradeJournal /> AG Grid + Supabase JS
  ├── <JournalForm /> 자동계산 포함
  └── SummaryCard 승률/손익비

4단계 — 주문/계좌
  ├── <OrderPanel /> KIS 주문
  └── <AccountPanel /> 잔고 조회

5단계 — 신규
  └── <ScenarioDrawing /> 미래 시나리오 드로잉
```

---

## 주요 난관

| 항목 | 내용 | 대응 |
|------|------|------|
| KIS WebSocket | Python asyncio 전용 → 브라우저 직접 연결 불가 | FastAPI WebSocket 중계 |
| FinanceDataReader | Python 전용 라이브러리 | FastAPI 엔드포인트로 유지 |
| `st.data_editor` | 인라인 편집 + 삭제 + 정렬 | AG Grid Community |
| 계산 로직 이전 | `_breakout_tab` 200줄 Python → TS | 순수 함수라 포팅 비교적 쉬움 |
| 다크 테마 | Streamlit 기본 제공 | Tailwind `dark:` 클래스 + CSS 변수 |
