import streamlit as st
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

from data_loader import StockDataLoader
from calculator import StrategyCalculator

# 컴포넌트 임포트
from components.styles import apply_custom_styles
from components.sidebar import render_sidebar
from components.settings_panel import render_settings_panel
from components.chart import render_chart
from components.scenario_cards import render_scenario_cards
from components.order_panel import render_order_input, render_order_status
from components.account_panel import render_account_panel

load_dotenv()

# --- 페이지 설정 ---
st.set_page_config(
    page_title="자동매매 시각화 봇 V2 (Pro Edition)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 커스텀 스타일 적용
apply_custom_styles()

import threading
import asyncio
from kis_websocket import KISWebSocket

GLOBAL_PRICES = {}
GLOBAL_WS_STATUS = {"status": "연결 대기 중 🟡", "last_time": "없음"}
WS_CLIENT = None
WS_LOOP = None

@st.cache_resource
def init_websocket():
    global WS_CLIENT, WS_LOOP
    WS_CLIENT = KISWebSocket(acc_idx=4)
    WS_LOOP = asyncio.new_event_loop()
    
    async def ws_callback(code, price):
        GLOBAL_PRICES[code] = price
        GLOBAL_WS_STATUS["last_time"] = datetime.now().strftime("%H:%M:%S")
        
    def run_ws():
        asyncio.set_event_loop(WS_LOOP)
        async def main():
            if await WS_CLIENT.connect():
                GLOBAL_WS_STATUS["status"] = f"연결 완료 🟢 ({datetime.now().strftime('%H:%M:%S')})"
                await WS_CLIENT.subscribe("005930") # 기본 삼성전자
                await WS_CLIENT.receive_loop(ws_callback)
            else:
                GLOBAL_WS_STATUS["status"] = "연결 실패 🔴"
        WS_LOOP.run_until_complete(main())
        
    t = threading.Thread(target=run_ws, daemon=True)
    t.start()
    return WS_CLIENT

ws_inst = init_websocket()

if "watch_orders" not in st.session_state:
    from supabase_db import SupabaseDB
    if SupabaseDB.is_connected():
        try:
            db_orders = SupabaseDB.fetch_watch_orders()
            restored = []
            for o in db_orders:
                is_o = not o.get("stock_code", "").isdigit()
                u = "$" if is_o else "원"
                t_p = o.get("target_price", 0)
                fmt_t_p = f"{t_p:,.2f}" if is_o else f"{int(t_p):,}"
                
                restored.append({
                    "id": o.get("id"),
                    "code": o.get("stock_code"),
                    "name": o.get("stock_name"),
                    "type": o.get("order_type"),
                    "strat": o.get("strat_name"),
                    "time": o.get("created_at")[11:19] if o.get("created_at") else "00:00:00",
                    "status": o.get("status"),
                    "target_price": t_p,
                    "qty": o.get("qty"),
                    "desc": f"{fmt_t_p}{u} 이하 도달 후 1.0%↑ 반등 시 매수"
                })
            st.session_state.watch_orders = restored
        except Exception as e:
            st.session_state.watch_orders = []
    else:
        st.session_state.watch_orders = []

if "registered_orders" not in st.session_state:
    st.session_state.registered_orders = []

# --- 데이터 캐싱 (성능 향상) ---
@st.cache_data(ttl=600)
def cached_ohlcv(symbol, count, period):
    return StockDataLoader.get_ohlcv(symbol, count, period)

@st.cache_data(ttl=3600)
def cached_stock_info_v2(search_input):
    return StockDataLoader.get_stock_info(search_input)

@st.cache_data(ttl=60)
def cached_current_price(symbol):
    return StockDataLoader.get_current_price(symbol)

# --- 1. 사이드바 (앱 정보 및 실시간 수치 요약) ---
status_placeholder = render_sidebar()

# --- 2. 상단 레이아웃 (차트 vs 설정패널) ---
top_left, top_right = st.columns([7, 3])

# 검색창을 차트 바로 위 콤팩트 레이아웃으로 배치
with top_left:
    col_ctl0, col_ctl1, col_ctl2, col_ctl3 = st.columns([2, 2, 3, 3])
    with col_ctl0:
        # 관심종목 클릭 시 값이 바뀌도록 key 설정 및 세션 상태 관리
        if "search_input_val" not in st.session_state:
            st.session_state.search_input_val = "005930"
            
        search_input = st.text_input(
            "종목 검색", 
            value=st.session_state.search_input_val, 
            placeholder="이름 또는 코드", 
            label_visibility="collapsed",
            key="search_input_widget"
        )
        # 위젯 입력값이 바뀌면 세션값도 동기화
        st.session_state.search_input_val = search_input

# 데이터 로딩 및 정보 추출
stock_info = cached_stock_info_v2(search_input.strip())
symbol = stock_info['symbol']
name = stock_info['name']

# 해외 주식 여부 판별 (영문 티커인 경우)
is_overseas = not symbol.isdigit()
unit = "$" if is_overseas else "원"
st.session_state.is_overseas = is_overseas
st.session_state.unit = unit

# 현재가 조회 (웹소켓 우선, 없으면 캐시)
c_price_raw = GLOBAL_PRICES.get(symbol)
if not c_price_raw:
    c_price_raw = cached_current_price(symbol)
    
c_price = float(c_price_raw) if c_price_raw else (150.0 if is_overseas else 70000.0)
if is_overseas:
    c_price_val = f"{c_price:,.2f} {unit}" if c_price_raw else "가격 정보 없음"
else:
    c_price_val = f"{int(c_price):,} {unit}" if c_price_raw else "가격 정보 없음"

# --- 시스템 상태 실시간 업데이트 (사이드바) ---
ws_st = GLOBAL_WS_STATUS["status"]
ws_time = GLOBAL_WS_STATUS["last_time"]
status_placeholder.markdown(f"""
    - **연결**: {ws_st}
    - **수신**: {ws_time}
""")

# --- 상태 유지 및 종목 변경 감지 로직 ---
if "last_symbol" not in st.session_state or st.session_state.last_symbol != symbol:
    st.session_state.last_symbol = symbol
    # 해외 주식은 소수점 유지, 국내 주식은 정수 유지
    st.session_state.ch_top = float(c_price) if is_overseas else int(c_price)
    st.session_state.ch_bot = float(c_price * 0.90) if is_overseas else int(c_price * 0.90)
    st.session_state.ct_input = float(c_price) if is_overseas else int(c_price)
    st.session_state.cb_input = float(c_price * 0.90) if is_overseas else int(c_price * 0.90)
    st.session_state.resist_input = float(c_price) if is_overseas else int(c_price)
    
    # 웹소켓 동적 구독 요청
    if WS_CLIENT and WS_LOOP:
        try:
            asyncio.run_coroutine_threadsafe(WS_CLIENT.subscribe(symbol), WS_LOOP)
        except Exception as e:
            pass

with top_left:
    with col_ctl1:
        st.markdown(f"""
            <div style='display: flex; flex-direction: column; padding-top: 2px; gap: 0;'>
                <div>
                    <span style='font-size: 0.95rem; font-weight: bold;'>{name}</span>
                    <span style='font-size: 0.7rem; color: #d1d4dc;'>({symbol})</span>
                </div>
                <div style='font-size: 0.9rem; font-weight: bold; color: #2ecc71;'>{c_price_val}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with col_ctl2:
        ws_status_str = "연결 대기 중 🟡"
        if WS_CLIENT and WS_CLIENT.is_running:
            ws_status_str = "연결 완료 🟢"
            if GLOBAL_WS_STATUS.get("last_time", "없음") != "없음":
                ws_status_str += f" ({GLOBAL_WS_STATUS['last_time']})"
        elif WS_CLIENT and not WS_CLIENT.is_running:
            ws_status_str = "연결 실패 🔴"
            

# --- 3. 설정 패널 (상단 우측) ---
with top_right:
    params = render_settings_panel(c_price)

mid_term = params["mid_term"]
short_term = params["short_term"]

# 단기 전략 연산 로직
st_sum_w = sum(short_term["weights"])
st_prices = []
st_alloc = []
st_avg_price = 0
st_hard_sl = 0
st_partial_sl = 0
st_loss = 0
partial_cut_w = short_term.get("partial_cut_weight", 0)

if st_sum_w > 0:
    resist_price = short_term["resist_price"]
    st_budget = short_term["budget"]
    st_prices = [resist_price * 1.02, resist_price * 0.98, resist_price * 0.94, resist_price * 0.91]
    st_alloc = [(w / st_sum_w) * st_budget for w in short_term["weights"]]
    st_avg_price = sum(p * a for p, a in zip(st_prices, st_alloc)) / st_budget if st_budget > 0 else 0
    
    # 1. 하드 손절가: "저항선 가격" 대비 사용자가 설정한 하드 손절 폭(%) 적용
    st_hard_sl_pct = short_term.get("hard_sl_pct", 10.0)
    st_hard_sl = resist_price * (1 - st_hard_sl_pct / 100)
    
    # 2. 부분 손절가: "저항선 가격" 대비 사용자가 설정한 부분 손절 폭(%) 적용
    st_partial_sl_pct = short_term.get("partial_sl_pct", 4.0)
    st_partial_sl = resist_price * (1 - st_partial_sl_pct / 100)

    # 3. 손실액 계산 (전체 예산 비중 기준)
    partial_cut_amt = (partial_cut_w / st_sum_w) * st_budget if st_sum_w > 0 else 0
    
    # [1단계] 부분 손절 확정 손실
    st_partial_loss = partial_cut_amt * (1 - (st_partial_sl / st_avg_price)) if st_avg_price > 0 else 0
    
    # [2단계] 나머지 잔량 하드 손절 손실 (평단가와 저항선 기준 하드손절가 사이의 이격률 계산)
    remaining_amt = st_budget - partial_cut_amt
    st_final_loss = remaining_amt * (1 - (st_hard_sl / st_avg_price)) if st_avg_price > 0 else 0
    
    # 최종 손실액 합산
    st_loss = st_partial_loss + st_final_loss
    
    # [비교용] 부분 손절 없을 경우의 손실률 (%)
    st_loss_no_partial = (1 - (st_hard_sl / st_avg_price)) * 100 if st_avg_price > 0 else 0

# --- 4. 차트 분석 영역 (상단 좌측) ---
df_ohlcv = None
calc_res = None
rr_targets = None

with top_left:
    with col_ctl2:
        candle_count = st.slider("캔들 수", 100, 2000, 500, label_visibility="collapsed")
    with col_ctl3:
        period_option = st.radio("주기", ["일봉", "주봉"], horizontal=True, label_visibility="collapsed")
        show_rsi = st.checkbox("RSI", value=False, key="show_rsi")
    
    period_code = 'D' if period_option == "일봉" else 'W'
    df_ohlcv = cached_ohlcv(symbol, count=candle_count, period=period_code)
    
    if df_ohlcv is not None and not df_ohlcv.empty:
        try:
            calc_res = StrategyCalculator.calculate_pyramid(
                channel_top=float(mid_term["channel_top"]),
                channel_bot=float(mid_term["channel_bot"]),
                hard_stop_loss=float(mid_term["hard_sl"]),
                base_budget=float(mid_term["budget"]),
                weights=mid_term["weights"]
            )
            rr_targets = StrategyCalculator.calculate_rr_targets(
                avg_price=calc_res['avg_price'],
                hard_stop_loss=calc_res['hard_stop_loss'],
                rr_multipliers=mid_term["rr_targets"]
            )
            
            # 차트 렌더링
            render_chart(df_ohlcv, mid_term, short_term, calc_res, rr_targets, st_avg_price, st_hard_sl, c_price, st_partial_sl=st_partial_sl)

            # 시나리오 카드 렌더링
            render_scenario_cards(mid_term, short_term, c_price, st_avg_price, st_hard_sl, st_sum_w, st_prices, short_term["weights"], st_alloc, short_term["budget"], st_loss, symbol=symbol, name=name, st_partial_sl=st_partial_sl, partial_cut_weight=partial_cut_w, st_loss_no_partial=st_loss_no_partial)
            
        except Exception as e:
            st.error(f"계산 중 오류 발생: {e}")
    else:
        st.warning("데이터를 불러올 수 없습니다. 종목 코드를 확인해 주세요.")

st.divider()

# --- 5. 하단 레이아웃 (주문/계좌 vs 주문창) ---
bottom_left, bottom_right = st.columns([7, 3])

if df_ohlcv is not None and not df_ohlcv.empty and calc_res is not None:
    with bottom_right:
        render_order_input(symbol, name, c_price, mid_term=mid_term)
        
    with bottom_left:
        render_order_status(symbol, name, c_price)
        render_account_panel(c_price)

st.divider()
st.caption("본 프로그램은 네이버 금융 데이터를 활용하며, 투자 판단의 책임은 사용자 본인에게 있습니다. 실행: streamlit run app.py")
