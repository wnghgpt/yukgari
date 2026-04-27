import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_lightweight_charts import renderLightweightCharts
from data_loader import StockDataLoader
from calculator import StrategyCalculator

# --- 페이지 설정 ---
st.set_page_config(
    page_title="자동매매 시각화 봇 V2 (Pro Edition)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 커스텀 스타일 ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #2a2e39; }
    div[data-testid="stExpander"] { border: 1px solid #2a2e39; border-radius: 10px; }
    
    /* 여백 최소화 (상단 바 가림 방지) */
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"],
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* 1. 전체 컴포넌트 간 수직 간격 축소 */
    div[data-testid="stVerticalBlock"] {
        gap: 0.7rem !important;
    }
    
    /* 2. 구분선(hr) 상하 여백 축소 */
    hr {
        margin-top: 7px !important;
        margin-bottom: 7px !important;
        border-color: #2a2e39 !important;
    }
    
    /* 3. 멀티셀렉트(목표가) 박스 높이/패딩 축소 */
    div[data-testid="stMultiSelect"] > div:first-child {
        padding: 0px !important;
        min-height: 24px !important;
    }
    div[data-testid="stMultiSelect"] div[role="button"] {
        padding: 1px 4px !important;
        min-height: 22px !important;
        font-size: 0.75rem !important;
    }
    div[data-testid="stMultiSelect"] span {
        font-size: 0.75rem !important;
    }
    
    /* 검색창 및 입력 박스 크기/폰트 축소 */
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {
        font-size: 0.8rem !important;
        padding: 4px 8px !important;
        height: 30px !important;
    }
    
    /* 입력창 라벨 폰트 축소 및 여백 제거 */
    div[data-testid="stNumberInput"] label {
        font-size: 0.75rem !important;
        margin-bottom: 0px !important;
        padding-bottom: 2px !important;
    }
    
    /* 컨테이너 테두리 내부 여백 축소 */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 10px !important;
    }
    
    /* 숫자 입력 박스 +, - 버튼 숨기기 */
    button[data-testid="stNumberInputStepDown"],
    button[data-testid="stNumberInputStepUp"] {
        display: none !important;
    }
    /* 버튼이 사라진 공간만큼 입력창 너비 확장 */
    div[data-testid="stNumberInput"] div[role="group"] > div {
        width: 100% !important;
    }
    </style>
""", unsafe_allow_html=True)

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
with st.sidebar:
    st.title("📈 시각화 봇 V2")
    st.info("한투 API 의존성이 제거된 분석 전용 버전입니다.")
    st.divider()
    
    # 전략 수치 요약 상시 표시 (사이드바)
    st.markdown("#### 📊 전략 요약")
    placeholder_summary = st.empty()
    
    st.divider()
    
    # 🔍 종목 코드 조회기 추가
    st.markdown("#### 🔍 종목 코드 조회")
    lookup_name = st.text_input("조회할 종목명 입력", placeholder="예: 카카오", key="lookup_input", label_visibility="collapsed")
    if lookup_name.strip():
        local_list = StockDataLoader.get_stock_list()
        lookup_results = []
        query = lookup_name.strip().upper()
        if local_list:
            for name, code in local_list.items():
                if query in name.upper():
                    lookup_results.append({"name": name, "symbol": code})
                    
        if lookup_results:
            for item in lookup_results[:5]:
                st.markdown(f"`{item['name']}` : **{item['symbol']}**")
        else:
            st.markdown("<span style='color: #ef5350; font-size: 0.8rem;'>조회 결과 없음</span>", unsafe_allow_html=True)
            
    st.divider()
    
# --- 2. 메인 레이아웃 (차트 vs 설정패널) ---
left_col, right_col = st.columns([7, 3])

# 검색창을 차트 바로 위 콤팩트 레이아웃으로 배치하기 위한 nested columns
with left_col:
    col_ctl0, col_ctl1, col_ctl2, col_ctl3 = st.columns([2, 2, 3, 3])
    with col_ctl0:
        search_input = st.text_input("종목 검색", value="삼성전자", placeholder="이름 또는 코드", label_visibility="collapsed")

# 데이터 로딩 및 정보 추출
stock_info = cached_stock_info_v2(search_input.strip())
symbol = stock_info['symbol']
name = stock_info['name']

# 현재가 조회
c_price_raw = cached_current_price(symbol)
c_price = c_price_raw if c_price_raw else 70000
c_price_val = f"{int(c_price):,} 원" if c_price_raw else "가격 정보 없음"

# --- 상태 유지 및 종목 변경 감지 로직 ---
if "last_symbol" not in st.session_state or st.session_state.last_symbol != symbol:
    st.session_state.last_symbol = symbol
    st.session_state.ch_top = int(c_price)
    st.session_state.ch_bot = int(c_price * 0.90)
    # 위젯의 내부 상태 캐시까지 강제 초기화
    st.session_state.ct_input = int(c_price)
    st.session_state.cb_input = int(c_price * 0.90)
    st.session_state.resist_input = int(c_price)

with left_col:
    with col_ctl1:
        # 종목명, 코드, 현재가를 깔끔하게 배치
        st.markdown(f"""
            <div style='display: flex; flex-direction: column; padding-top: 2px; gap: 0;'>
                <div>
                    <span style='font-size: 0.95rem; font-weight: bold;'>{name}</span>
                    <span style='font-size: 0.7rem; color: #d1d4dc;'>({symbol})</span>
                </div>
                <div style='font-size: 0.9rem; font-weight: bold; color: #2ecc71;'>{c_price_val}</div>
            </div>
        """, unsafe_allow_html=True)

with right_col:
    st.markdown("<div style='font-size: 0.95rem; font-weight: bold; margin-bottom: 10px; color: #3498DB;'>⚙️ 전략 시뮬레이션</div>", unsafe_allow_html=True)
    
    with st.expander("📊 중기: 채널 내 분할매수", expanded=True):
        # 1. 최상단 보조선 체크박스 & 목표가 손익비
        col_title, col_chk = st.columns([7, 3])
        with col_title:
            st.markdown("<div style='font-size: 0.85rem; font-weight: bold; color: #3498DB;'>🎯 목표가 손익비 (RR)</div>", unsafe_allow_html=True)
        st.markdown("""
        <style>
        .stCheckbox label p {
            font-size: 0.7rem !important;
            white-space: nowrap !important;
            color: #d1d4dc !important;
        }
        </style>
        """, unsafe_allow_html=True)
        with col_chk:
            show_lines_user = st.checkbox("보조선", value=True, key="show_user_lines")
            
        rr_targets_sel = st.multiselect("🎯 RR 목표가 표시", [2, 3, 5, 10, 15, 20], default=[3], label_visibility="collapsed")
        
        st.markdown("<hr style='margin: 10px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)
        
        # 2. 채널 범위 설정
        st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 10px; color: #3498DB;'>📏 채널 범위 설정</div>", unsafe_allow_html=True)
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if "ct_input" not in st.session_state:
                st.session_state.ct_input = int(c_price)
            channel_top = st.number_input("상단(저항)", step=100, key="ct_input")
            st.session_state.ch_top = channel_top
        with col_c2:
            if "cb_input" not in st.session_state:
                st.session_state.cb_input = int(c_price * 0.90)
            channel_bot = st.number_input("하단(지지)", step=100, key="cb_input")
            st.session_state.ch_bot = channel_bot
            
        hard_sl = int(channel_bot * 0.96)
        
        col_h1, col_h2 = st.columns([6, 4])
        with col_h1:
            st.markdown(f"<p style='font-size: 0.85rem; color: #d1d4dc; margin-top: 2px; margin-bottom: 0;'>최종 손절선 (-4%)</p>", unsafe_allow_html=True)
        with col_h2:
            st.markdown(f"<p style='font-size: 0.95rem; font-weight: bold; text-align: right; margin-top: 2px; margin-bottom: 0;'>{hard_sl:,} 원</p>", unsafe_allow_html=True)
            
        st.markdown("<hr style='margin: 10px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)
        
        # 3. 진입 금액 및 비중 통합
        st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 10px; color: #3498DB;'>💰 진입 금액 및 비중</div>", unsafe_allow_html=True)
        
        col_b1, col_b2 = st.columns([4, 6])
        with col_b1:
            st.markdown("<p style='font-size: 0.85rem; font-weight: bold; margin-top: 5px; margin-bottom: 0;'>투입 금액</p>", unsafe_allow_html=True)
        with col_b2:
            total_budget = st.number_input("총 투입 예산(원)", value=3000000, step=100000, label_visibility="collapsed", key="budget_input")
            

        
        col_w1, col_w2, col_w3, col_w4 = st.columns(4)
        with col_w1: w1 = st.number_input("1차", 0, 100, 3, key="w1_input")
        with col_w2: w2 = st.number_input("2차", 0, 100, 3, key="w2_input")
        with col_w3: w3 = st.number_input("3차", 0, 100, 3, key="w3_input")
        with col_w4: w4 = st.number_input("4차", 0, 100, 0, key="w4_input")
        
        weights = [float(w1), float(w2), float(w3), float(w4)]

    with st.expander("⚖️ 단기: 돌파 시 진입 + 풀백 매수", expanded=False):
        col_st_title, col_st_chk = st.columns([7, 3])
        with col_st_title:
            st.markdown("<div style='font-size: 0.85rem; font-weight: bold; color: #E74C3C;'>🎯 RR 목표가 표시</div>", unsafe_allow_html=True)
        with col_st_chk:
            show_lines_short = st.checkbox("보조선", value=False, key="show_short_lines")
            
        st_rr_targets_sel = st.multiselect("🎯 단기 RR 목표가 표시", [2, 3, 5, 10, 15, 20], default=[3], label_visibility="collapsed", key="st_rr_targets")
        
        st.markdown("<hr style='margin: 10px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 10px; color: #E74C3C;'>📏 저항선 가격 설정</div>", unsafe_allow_html=True)
        
        if "resist_input" not in st.session_state:
            st.session_state.resist_input = int(c_price)
            
        resist_price = st.number_input("저항선 가격 (원)", step=100, key="resist_input", label_visibility="collapsed")
        
        st.markdown("<hr style='margin: 10px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 10px; color: #E74C3C;'>💰 단기 투자 예산 및 비중</div>", unsafe_allow_html=True)
        
        col_st_b1, col_st_b2 = st.columns([4, 6])
        with col_st_b1:
            st.markdown("<p style='font-size: 0.85rem; font-weight: bold; margin-top: 5px; margin-bottom: 0;'>투입 금액</p>", unsafe_allow_html=True)
        with col_st_b2:
            st_budget = st.number_input("단기 예산(원)", value=3000000, step=100000, label_visibility="collapsed", key="st_budget_input")
            
        st.markdown("<p style='font-size: 0.8rem; color: #d1d4dc; margin-top: 8px; margin-bottom: 2px;'>1~4차 진입 비중</p>", unsafe_allow_html=True)
        
        col_stw1, col_stw2, col_stw3, col_stw4 = st.columns(4)
        with col_stw1: st_w1 = st.number_input("1차 비중", 0, 100, 1, key="st_w1_input", label_visibility="collapsed")
        with col_stw2: st_w2 = st.number_input("2차 비중", 0, 100, 1, key="st_w2_input", label_visibility="collapsed")
        with col_stw3: st_w3 = st.number_input("3차 비중", 0, 100, 1, key="st_w3_input", label_visibility="collapsed")
        with col_stw4: st_w4 = st.number_input("4차 비중", 0, 100, 1, key="st_w4_input", label_visibility="collapsed")
        
        # 연산 로직
        st_weights = [float(st_w1), float(st_w2), float(st_w3), float(st_w4)]
        st_sum_w = sum(st_weights)
        if st_sum_w > 0:
            st_prices = [resist_price * 1.02, resist_price * 0.98, resist_price * 0.94, resist_price * 0.91]
            st_alloc = [(st_w / st_sum_w) * st_budget for st_w in st_weights]
            st_avg_price = sum(p * a for p, a in zip(st_prices, st_alloc)) / st_budget if st_budget > 0 else 0
            st_hard_sl = resist_price * 0.90
            st_loss = st_budget * (1 - (st_hard_sl / st_avg_price)) if st_avg_price > 0 else 0
            
            pass
    with st.expander("장기: 조정 시 매집", expanded=False):
        st.markdown("<p style='font-size: 0.8rem; color: #d1d4dc;'>차트 보조선 출력 및 개별 파라미터 설정 예정 공간</p>", unsafe_allow_html=True)

# --- 4. 차트 분석 영역 ---
with left_col:
    with col_ctl2:
        candle_count = st.slider("캔들 수", 100, 2000, 500, label_visibility="collapsed")
    with col_ctl3:
        period_option = st.radio("주기", ["일봉", "주봉"], horizontal=True, label_visibility="collapsed")
    
    period_code = 'D' if period_option == "일봉" else 'W'
    
    df_ohlcv = cached_ohlcv(symbol, count=candle_count, period=period_code)
    
    if df_ohlcv is not None and not df_ohlcv.empty:
        # 전략 계산
        try:
            calc_res = StrategyCalculator.calculate_pyramid(
                channel_top=float(channel_top),
                channel_bot=float(channel_bot),
                hard_stop_loss=float(hard_sl),
                base_budget=float(total_budget),
                weights=weights
            )
            rr_targets = StrategyCalculator.calculate_rr_targets(
                avg_price=calc_res['avg_price'],
                hard_stop_loss=calc_res['hard_stop_loss'],
                rr_multipliers=rr_targets_sel
            )
            
            # 사이드바 요약 업데이트
            placeholder_summary.markdown(f"""
                - **평단**: {int(calc_res['avg_price']):,}원
                - **손실률**: {calc_res['loss_pct']:.2f}%
            """)
            
            pass
            
            # --- 차트 데이터 구성 ---
            plot_df = df_ohlcv.sort_values('Date', ascending=True)
            candles = []
            volume_data = []
            
            for _, row in plot_df.iterrows():
                time_val = row['Date'].strftime('%Y-%m-%d') if isinstance(row['Date'], (pd.Timestamp, datetime)) else str(row['Date'])[:10]
                candles.append({
                    "time": time_val,
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close'])
                })
                volume_data.append({
                    "time": time_val,
                    "value": float(row['Volume']),
                    "color": 'rgba(38, 166, 154, 0.5)' if row['Close'] >= row['Open'] else 'rgba(239, 83, 80, 0.5)'
                })
            
            # 시리즈 구성
            series = [
                {
                    "type": "Candlestick",
                    "data": candles,
                    "options": {
                        "upColor": "#26a69a", "downColor": "#ef5350",
                        "borderVisible": False, "wickUpColor": "#26a69a", "wickDownColor": "#ef5350",
                        "priceLineColor": "#7FFF00"
                    }
                },
                {
                    "type": "Histogram",
                    "data": volume_data,
                    "options": {
                        "color": "#26a69a",
                        "priceFormat": {"type": "volume"},
                        "priceScaleId": "", # Overlay mode
                    },
                    "priceScale": {
                        "scaleMargins": {"top": 0.8, "bottom": 0}
                    }
                }
            ]
            
            # 수평선 추가 (오버레이 함수)
            def add_line(price, color, style, title, width=1):
                line_data = [{"time": c["time"], "value": price} for c in candles]
                series.append({
                    "type": "Line",
                    "data": line_data,
                    "options": {
                        "color": color, "lineWidth": width, "lineStyle": style,
                        "title": title, "crosshairMarkerVisible": False,
                        "priceLineVisible": False, "lastValueVisible": True
                    }
                })

            if show_lines_user:
                # 매수 구역들
                for i, zone in enumerate(calc_res['zones']):
                    lbl = f"{i+1}차"
                    add_line(zone['price'], "#FFFF00", 2, lbl)
                
                # 중요 라인들
                add_line(calc_res['avg_price'], "#FF9800", 0, "평단", width=2)
                add_line(calc_res['hard_stop_loss'], "#E74C3C", 0, "손절")
                add_line(channel_top, "#FFFFFF", 0, "상단")
                add_line(channel_bot, "#FFFFFF", 0, "하단")
                
                # 목표가들
                for label, price in rr_targets.items():
                    simple_lbl = label.replace("RR_", "").replace("x", "배")
                    add_line(price, "#2ECC71", 0, simple_lbl)
                    
            if show_lines_short:
                add_line(resist_price, "#FFFFFF", 0, "저항")
                add_line(resist_price * 1.10, "#3498DB", 0, "10%")
                # 옐로우 골드 분할 매수선 (1~4차)
                add_line(resist_price * 1.02, "#FFFF00", 2, "1차(돌파)")
                add_line(resist_price * 0.98, "#FFFF00", 2, "2차")
                add_line(resist_price * 0.94, "#FFFF00", 2, "3차")
                add_line(resist_price * 0.91, "#FFFF00", 2, "4차")
                
                if 'st_avg_price' in locals():
                    add_line(st_avg_price, "#FF9800", 0, "평단", width=2)
                    add_line(st_hard_sl, "#FF3131", 0, "-10%")
                    
                    # 단기 RR 목표가 표시 (사용자 정의)
                    st_risk = st_avg_price - st_hard_sl
                    if st_risk > 0 and 'st_rr_targets_sel' in locals():
                        for rr_val in st_rr_targets_sel:
                            rr_price = st_avg_price + (st_risk * rr_val)
                            add_line(rr_price, "#2ECC71", 0, f"{rr_val}배")

            # 차트 옵션
            chart_options = {
                "height": 500,
                "layout": {
                    "background": {"type": "solid", "color": "#131722"}, 
                    "textColor": "#d1d4dc",
                    "fontSize": 8 # 글씨 크기 추가 축소
                },
                "grid": {"vertLines": {"color": "rgba(42, 46, 57, 0)"}, "horzLines": {"color": "rgba(42, 46, 57, 0.5)"}},
                "crosshair": {"mode": 0},
                "timeScale": {"borderColor": "rgba(197, 203, 206, 0.8)", "rightOffset": 40}
            }
            
            renderLightweightCharts([{"chart": chart_options, "series": series}], key='chart_v2')
            
            # --- 차트 하단: 4가지 시나리오 가로 병렬 배치 ---
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom: 15px;'>📍 분할 매수 시나리오별 비교</h4>", unsafe_allow_html=True)
            
            sc_cols = st.columns(3)
            
            # 1번 카드 (중기)
            with sc_cols[0]:
                try:
                    sc_res = StrategyCalculator.calculate_pyramid(
                        channel_top=float(channel_top),
                        channel_bot=float(channel_bot),
                        hard_stop_loss=float(hard_sl),
                        base_budget=float(total_budget),
                        weights=weights
                    )
                    with st.container(border=True):
                        st.markdown(f"<h5 style='color: #3498DB; margin-bottom: 10px;'>📊 중기</h5>", unsafe_allow_html=True)
                        st.markdown(f"""
                            <div style='font-size: 0.8rem; line-height: 1.4;'>
                                <b>평단:</b> {int(sc_res['avg_price']):,}원 | <b>보유:</b> {int(sc_res['total_qty']):,}주<br>
                                <b style='color: #ef5350;'>손실: {sc_res['loss_pct']:.2f}%</b>
                            </div>
                            <hr style='margin: 8px 0;'>
                        """, unsafe_allow_html=True)
                        for i, zone in enumerate(sc_res['zones']):
                            lbl = f"{i+1}차" if i < 3 else "4차"
                            qty = int(zone['qty'])
                            amt_val = zone['allocate_amt'] / 10000
                            drop_pct = ((zone['price'] / c_price) - 1) * 100
                            color_pct = "#2ecc71" if drop_pct >= 0 else "#ef5350"
                            st.markdown(f"""
                                <div style='font-size: 0.65rem; white-space: nowrap; margin-bottom: 3px; display: flex; justify-content: space-between;'>
                                    <span><b>{lbl}:</b> {int(zone['price']):,}원 <span style='color: {color_pct}; font-size: 0.6rem;'>({drop_pct:+.1f}%)</span></span>
                                    <span style='color: #8a8d9a;'>{qty}주 ({amt_val:.1f}만)</span>
                                </div>
                            """, unsafe_allow_html=True)
                            
                        st.markdown(f"""
                            <div style='font-size: 0.78rem; color: #ef5350; display: flex; justify-content: space-between;'>
                                <b>손절선:</b>
                                <b>{int(sc_res['hard_stop_loss']):,}원</b>
                            </div>
                        """, unsafe_allow_html=True)
                except:
                    st.error("계산 오류")
                    
            # 2번 카드 (단기)
            with sc_cols[1]:
                if 'st_avg_price' in locals() and st_sum_w > 0:
                    try:
                        st_total_qty = int(st_budget / st_avg_price) if st_avg_price > 0 else 0
                        st_loss_pct = (st_loss / st_budget) * 100 if st_budget > 0 else 0
                        
                        with st.container(border=True):
                            st.markdown(f"<h5 style='color: #E74C3C; margin-bottom: 10px;'>⚖️ 단기</h5>", unsafe_allow_html=True)
                            st.markdown(f"""
                                <div style='font-size: 0.8rem; line-height: 1.4;'>
                                    <b>평단:</b> {int(st_avg_price):,}원 | <b>보유:</b> {st_total_qty:,}주<br>
                                    <b style='color: #ef5350;'>손실: {st_loss_pct:.2f}%</b>
                                </div>
                                <hr style='margin: 8px 0;'>
                            """, unsafe_allow_html=True)
                            
                            st_labels = ["1차", "2차", "3차", "4차"]
                            for i, (p, w) in enumerate(zip(st_prices, st_weights)):
                                amt = st_alloc[i]
                                qty = int(amt / p) if p > 0 else 0
                                amt_val = amt / 10000
                                drop_pct = ((p / c_price) - 1) * 100
                                color_pct = "#2ecc71" if drop_pct >= 0 else "#ef5350"
                                st.markdown(f"""
                                    <div style='font-size: 0.65rem; white-space: nowrap; margin-bottom: 3px; display: flex; justify-content: space-between;'>
                                        <span><b>{st_labels[i]}:</b> {int(p):,}원 <span style='color: {color_pct}; font-size: 0.6rem;'>({drop_pct:+.1f}%)</span></span>
                                        <span style='color: #8a8d9a;'>{qty}주 ({amt_val:.1f}만)</span>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                            st.markdown(f"""
                                <div style='font-size: 0.78rem; color: #ef5350; display: flex; justify-content: space-between;'>
                                    <b>손절선:</b>
                                    <b>{int(st_hard_sl):,}원</b>
                                </div>
                            """, unsafe_allow_html=True)
                    except:
                        st.error("계산 오류")
                else:
                    with st.container(border=True):
                        st.markdown(f"<h5 style='color: #E74C3C; margin-bottom: 10px;'>⚖️ 단기 전략</h5>", unsafe_allow_html=True)
                        st.markdown("<div style='font-size: 0.8rem; color:#8a8d9a;'>단기 전략 미설정</div>", unsafe_allow_html=True)
                        
            # 3번 카드
            with sc_cols[2]:
                with st.container(border=True):
                    st.markdown(f"<h5 style='color: #7f8c8d; margin-bottom: 10px;'>🛡️ 장기 </h5>", unsafe_allow_html=True)
                    st.markdown("<div style='height: 100px; display: flex; align-items: center; justify-content: center; color: #7f8c8d;'>-</div>", unsafe_allow_html=True)
                    

            
        except Exception as e:
            st.error(f"계산 중 오류 발생: {e}")
    else:
        st.warning("데이터를 불러올 수 없습니다. 종목 코드를 확인해 주세요.")

st.divider()
st.caption("본 프로그램은 네이버 금융 데이터를 활용하며, 투자 판단의 책임은 사용자 본인에게 있습니다. 실행: streamlit run app.py")

