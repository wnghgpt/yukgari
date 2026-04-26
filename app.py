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
    
# --- 1. 헤더: 종목 검색 및 상태 (미니멀리즘 슬림 레이아웃) ---
col_h1, col_h2 = st.columns([3, 7])

with col_h1:
    search_input = st.text_input("종목 검색", value="삼성전자", placeholder="이름 또는 코드", label_visibility="collapsed")

# 데이터 로딩 및 정보 추출
stock_info = cached_stock_info_v2(search_input.strip())
symbol = stock_info['symbol']
name = stock_info['name']

# 현재가 조회
c_price_raw = cached_current_price(symbol)
c_price = c_price_raw if c_price_raw else 70000 # 에러 방지용 기본값
c_price_val = f"{int(c_price):,} 원" if c_price_raw else "가격 정보 없음 (기본값 표시)"

# --- 상태 유지 및 종목 변경 감지 로직 ---
if "last_symbol" not in st.session_state or st.session_state.last_symbol != symbol:
    st.session_state.last_symbol = symbol
    # 종목이 바뀌었을 때만 채널 가격 초기화
    st.session_state.ch_top = int(c_price * 1.05)
    st.session_state.ch_bot = int(c_price * 0.95)
    # 예산이나 비중은 종목이 바뀌어도 유지하고 싶을 수 있으므로 주석 처리 또는 유지

with col_h2:
    # 종목명, 코드, 현재가를 한 줄로 깔끔하게 배치
    st.markdown(f"""
        <div style='display: flex; align-items: baseline; gap: 15px; padding-top: 5px;'>
            <span style='font-size: 1.5rem; font-weight: bold;'>{name}</span>
            <span style='font-size: 1rem; color: #d1d4dc;'>({symbol})</span>
            <span style='font-size: 1.3rem; font-weight: bold; color: #2ecc71; margin-left: auto;'>{c_price_val}</span>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# --- 2. 메인 레이아웃 (차트 vs 설정패널) ---
left_col, right_col = st.columns([7, 3])

with right_col:
    st.subheader("⚙️ 전략 시뮬레이션")
    
    # --- 유저 요청: RR 목표가 설정을 채널 설정 위로 이동 ---
    rr_targets_sel = st.multiselect("🎯 RR 목표가 표시", [2, 3, 5, 10, 15, 20], default=[3, 5])

    with st.container(border=True):
        st.markdown("##### 📏 채널 범위 설정")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            channel_top = st.number_input("상단(저항)", value=st.session_state.ch_top, step=100, key="ct_input")
            st.session_state.ch_top = channel_top # 수동 입력 즉시 반영
        with col_c2:
            channel_bot = st.number_input("하단(지지)", value=st.session_state.ch_bot, step=100, key="cb_input")
            st.session_state.ch_bot = channel_bot # 수동 입력 즉시 반영
        
        # 기계적 손절선 자동 제안 (지지선 대비 -4%)
        hard_sl = int(channel_bot * 0.96)
        
        col_h1, col_h2 = st.columns([6, 4])
        with col_h1:
            st.markdown(f"<p style='font-size: 0.9rem; color: #d1d4dc; margin-top: 5px;'>최종 손절선 (-4%)</p>", unsafe_allow_html=True)
        with col_h2:
            st.markdown(f"<p style='font-size: 1rem; font-weight: bold; text-align: right; margin-top: 5px;'>{hard_sl:,} 원</p>", unsafe_allow_html=True)
            
    with st.container(border=True):
        st.markdown("##### 📐 진입 비중")
        
        # 총 투입 예산
        col_b1, col_b2 = st.columns([4, 6])
        with col_b1:
            st.markdown("<p style='font-size: 0.9rem; font-weight: bold;'>총 투입 예산</p>", unsafe_allow_html=True)
        with col_b2:
            total_budget = st.number_input("총 투입 예산(원)", value=1000000, step=100000, label_visibility="collapsed", key="budget_input")
        
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        
        # 1~4차 개별 입력 박스 (4개 컬럼)
        col_w1, col_w2, col_w3, col_w4 = st.columns(4)
        with col_w1: w1 = st.number_input("1차", 0, 100, 3, key="w1_input")
        with col_w2: w2 = st.number_input("2차", 0, 100, 3, key="w2_input")
        with col_w3: w3 = st.number_input("3차", 0, 100, 3, key="w3_input")
        with col_w4: w4 = st.number_input("4차", 0, 100, 0, key="w4_input")
        
        weights = [float(w1), float(w2), float(w3), float(w4)]
        
    # --- 유저 요청: 타점 정보를 텍스트로 압축 노출 ---
    st.divider()
    st.markdown("##### 📍 실시간 타점 가이드")
    # (결과 렌더링은 아래 하단 script 영역에서 수행됨)
    
    # 전략 계산 (여기서 필요하므로 미리 계산하거나 위에서 가져옴)
    # 계산 로직을 위로 올리거나 결과를 공유해야 함. 
    # 현재 코드 구조상 아래에서 계산하므로, 계산 로직을 상단(레이아웃 분리 전)으로 이동하는 것이 좋음.

# --- 4. 차트 분석 영역 ---
with left_col:
    # --- 차트 컨트롤 (슬라이더: 왼쪽, 주기버튼: 오른쪽 끝) ---
    col_ctl1, col_ctl2, col_ctl3 = st.columns([5, 3, 2])
    with col_ctl1:
        candle_count = st.slider("가져올 캔들 수", 100, 2000, 500, label_visibility="collapsed")
    with col_ctl2:
        st.empty()  # 중앙 여백
    with col_ctl3:
        period_option = st.radio("캔들 주기", ["일봉", "주봉"], horizontal=True, label_visibility="collapsed")
    
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
                - **비상금**: {int(calc_res['extra_budget']):,}원
                - **손실률**: {calc_res['loss_pct']:.2f}%
            """)
            
            # 우측 패널에 타점 텍스트 출력 (압축 버전)
            with right_col:
                drop_texts = []
                for i, zone in enumerate(calc_res['zones']):
                    drop_pct = ((zone['price'] / c_price) - 1) * 100
                    lbl = f"{i+1}차" if i < 3 else "4차(비상)"
                    
                    # 투자액 및 수량 포맷팅
                    amt = zone['allocate_amt']
                    qty = int(zone['qty'])
                    amt_str = f"{amt/10000:.1f}만" if amt >= 10000 else f"{int(amt):,}원"
                    
                    drop_texts.append(
                        f"<b>{lbl}:</b> {int(zone['price']):,}원 <span style='color: #ef5350;'>({drop_pct:.1f}%)</span> | "
                        f"<span style='font-size: 0.85rem; color: #d1d4dc;'>{amt_str} ({qty}주)</span>"
                    )
                
                # 최종 손실 추가 (손실액 및 총 주식 수 포함)
                loss_amt = calc_res['total_risk_amount']
                total_qty = int(calc_res['total_qty'])
                drop_texts.append(
                    f"<hr style='margin: 5px 0;'>"
                    f"<b style='color: #ef5350;'>최종 기대 손실: {calc_res['loss_pct']:.2f}% (-{int(loss_amt):,}원)</b><br>"
                    f"<span style='font-size: 0.85rem; color: #d1d4dc;'>└ 총 {total_qty:,}주 보유 예정</span>"
                )
                
                # 줄간격을 최소화한 HTML 출력
                st.markdown(f"""
                    <div style='line-height: 1.1; font-size: 0.95rem; margin-top: -10px;'>
                        {''.join([f'<div style="margin-bottom: 2px;">{text}</div>' for text in drop_texts])}
                    </div>
                """, unsafe_allow_html=True)
            
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
                        "borderVisible": False, "wickUpColor": "#26a69a", "wickDownColor": "#ef5350"
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
            def add_line(price, color, style, title):
                line_data = [{"time": c["time"], "value": price} for c in candles]
                series.append({
                    "type": "Line",
                    "data": line_data,
                    "options": {
                        "color": color, "lineWidth": 1, "lineStyle": style,
                        "title": title, "crosshairMarkerVisible": False,
                        "priceLineVisible": False, "lastValueVisible": True
                    }
                })

            # 매구 구역들
            for i, zone in enumerate(calc_res['zones']):
                lbl = f"{i+1}차"
                clr = "#F1C40F" if i < 3 else "#E67E22"
                add_line(zone['price'], clr, 2, lbl)
            
            # 중요 라인들
            add_line(calc_res['avg_price'], "#3498DB", 2, "평단")
            add_line(calc_res['hard_stop_loss'], "#E74C3C", 0, "손절")
            add_line(channel_top, "#FFFFFF", 0, "상단")
            add_line(channel_bot, "#FFFFFF", 0, "하단")
            
            # 목표가들
            for label, price in rr_targets.items():
                simple_lbl = label.replace("RR_", "").replace("x", "배")
                add_line(price, "#2ECC71", 0, simple_lbl)

            # 차트 옵션
            chart_options = {
                "height": 600,
                "layout": {
                    "background": {"type": "solid", "color": "#131722"}, 
                    "textColor": "#d1d4dc",
                    "fontSize": 10 # 글씨 크기 축소
                },
                "grid": {"vertLines": {"color": "rgba(42, 46, 57, 0)"}, "horzLines": {"color": "rgba(42, 46, 57, 0.5)"}},
                "crosshair": {"mode": 0},
                "timeScale": {"borderColor": "rgba(197, 203, 206, 0.8)", "rightOffset": 40}
            }
            
            renderLightweightCharts([{"chart": chart_options, "series": series}], key='chart_v2')
            
        except Exception as e:
            st.error(f"계산 중 오류 발생: {e}")
    else:
        st.warning("데이터를 불러올 수 없습니다. 종목 코드를 확인해 주세요.")

st.divider()
st.caption("본 프로그램은 네이버 금융 데이터를 활용하며, 투자 판단의 책임은 사용자 본인에게 있습니다. 실행: streamlit run app.py")

