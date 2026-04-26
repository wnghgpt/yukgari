import streamlit as st
import pandas as pd
from streamlit_lightweight_charts import renderLightweightCharts
from kis_api import KISClient
from calculator import StrategyCalculator

st.set_page_config(page_title="자동매매 시각화 봇", layout="wide", initial_sidebar_state="expanded")

# --- 1. 백엔드 코어 연동 ---
@st.cache_resource
def get_kis():
    return KISClient()

kis = get_kis()

@st.cache_data(ttl=3600)
def get_stock_name(symbol: str) -> str:
    """네이버페이 증권 웹페이지에서 로딩 지연 없이 실시간 종목명을 낚아채옵니다."""
    try:
        import requests, re
        html = requests.get(f'https://finance.naver.com/item/main.naver?code={symbol}', timeout=2).text
        m = re.search(r'<title>(.*?)</title>', html)
        if m:
            # "삼성전자 : Npay 증권" -> "삼성전자"
            return m.group(1).split(':')[0].strip()
    except:
        pass
    return symbol

@st.cache_data(ttl=86400)
def translate_name_to_symbol(name: str) -> str:
    """사용자가 한글 종목명을 치면 코드로 자동 변환 (FinanceDataReader 활용)"""
    if not name or name.isdigit(): return name
    try:
        import FinanceDataReader as fdr
        df = fdr.StockListing("KRX")
        match = df[df['Name'] == name]
        if not match.empty:
            return match.iloc[0]['Code']
    except Exception as e:
        print("FDR Error:", e)
    return name

# --- 사이드바 (계좌 연동 영역) ---
with st.sidebar:
    st.title("💼 [내 계좌 현황]")
    
    # 예수금
    buyable_cash = kis.get_buyable_cash()
    st.metric(label="당장 매수 가능한 예수금", value=f"{buyable_cash:,} 원")
    st.divider()
    
    # 보유 종목
    st.markdown("**📊 현재 보유 종목 리스트**")
    my_stocks_df = kis.get_my_stocks()
    if my_stocks_df.empty:
        st.info("현재 보유 중인 주식이 없습니다.")
    else:
        st.dataframe(my_stocks_df, use_container_width=True, hide_index=True)

# --- 1. 메인 종목 검색 (헤더 영역으로 독립) ---
st.subheader("1단계: 차트 분석 및 타겟팅")
search_col1, search_col2, _ = st.columns([3, 4, 3])
with search_col1:
    raw_input = st.text_input("검색", "삼성전자", label_visibility="collapsed", placeholder="종목명 또는 코드 입력")
    symbol = translate_name_to_symbol(raw_input.strip())
    stock_name = get_stock_name(symbol)
    
with search_col2:
    if stock_name != symbol:
        st.markdown(f"🏷️ **{stock_name}** ({symbol})")

curr_price_resp = kis.get_current_price(symbol)
curr_price = curr_price_resp if curr_price_resp else 70000

st.divider()  # 검색부와 메인 컨트롤부를 가르는 시각적 분리선

# --- 2. 메인 화면 레이아웃 (차트 vs 옵션박스 완벽 수직정렬) ---
left_col, right_col = st.columns([7, 3])

# --- 우측 컨트롤 패널 창 ---
with right_col:
    with st.expander("⚙️ 2단계: 피라미딩 조건 통제소", expanded=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            channel_top = st.number_input("상단(저항선)", min_value=1, value=int(curr_price * 1.05), step=100)
        with col_c2:
            channel_bot = st.number_input("하단(지지선)", min_value=1, value=int(curr_price * 0.95), step=100)
            
        # 기계적 찐손절은 하단(손절선)에서 무조건 -4% 자동 세팅
        hard_sl = channel_bot * 0.96
        
        total_budget = st.number_input("1~3차 총 투입 예산(원)", min_value=10000, value=1000000, step=100000)
        
        st.write("📐 타점 세부 진입 비중 (1~10)")
        col_w1, col_w2, col_w3, col_w4 = st.columns(4)
        with col_w1:
            w1 = st.slider("1차", 1, 10, 2)
        with col_w2:
            w2 = st.slider("2차", 1, 10, 3)
        with col_w3:
            w3 = st.slider("3차", 1, 10, 5)
        with col_w4:
            w4 = st.slider("4차(비상)", 0, 10, 2)
        weights = [w1, w2, w3, w4]
        
        rr_target_options = st.multiselect("✅ 목표 수익비가(RR) 차트 표시", [2, 3, 5, 10], default=[3, 5])
    
    st.divider()
    st.subheader("3단계: 예약 실행")
    if st.button("🚀 위 조건으로 매수/매도 동시 예약 전송", use_container_width=True, type="primary"):
        st.success("예약이 체결 대기열에 들어갔습니다! (실제 API 주문 기능 적용 대기중)")
        st.balloons()

# --- 좌측 메인 차트 ---
with left_col:
    # 차트 바로 위 장착된 라디오 버튼 (간격 최소화)
    period_option = st.radio("캔들 기준", ["일봉", "주봉"], horizontal=True, label_visibility="collapsed")
    period_code = 'D' if period_option == "일봉" else 'W'
    
    df_candles = kis.get_ohlcv(symbol, period_code)
    
    if df_candles is not None and not df_candles.empty:
        try:
            # 수학 계산 엔진 가동 (UI 입력값 -> 수식 계산기)
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
                rr_multipliers=rr_target_options
            )
            
            # --- TradingView (Lightweight) 차트 및 오버레이 그리기 ---
            plot_df = df_candles.reset_index(names='Date') if 'Date' not in df_candles.columns else df_candles
            # 트레이딩뷰 차트는 반드시 과거->현재 순(오름차순)이어야만 렌더링되므로 정렬 필수
            plot_df = plot_df.sort_values('Date', ascending=True)
            
            # 캔들 데이터 변환
            candles = []
            for _, row in plot_df.iterrows():
                # 시간 포맷 맞추기 (YYYY-MM-DD 형식이 가장 안전)
                time_str = str(row['Date'])[:10]
                candles.append({
                    "time": time_str,
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close'])
                })
            
            # 캔들 데이터 배열
            seriesCandlestickChart = [{
                "type": "Candlestick",
                "data": candles,
                "options": {
                    "upColor": "#26a69a",
                    "downColor": "#ef5350",
                    "borderVisible": False,
                    "wickUpColor": "#26a69a",
                    "wickDownColor": "#ef5350"
                }
            }]
            
            # 수평선을 래퍼에서 지원하지 않으므로, 전체 기간에 동일한 값을 가진 Line Series 로 오버레이(우회 구현)
            def add_horizontal_line(price: float, color: str, style: int, title: str):
                line_data = [{"time": c["time"], "value": price} for c in candles]
                seriesCandlestickChart.append({
                    "type": "Line",
                    "data": line_data,
                    "options": {
                        "color": color,
                        "lineWidth": 2,
                        "lineStyle": style, # 0: Solid, 2: Dashed
                        "title": title,
                        "crosshairMarkerVisible": False,
                        "priceLineVisible": False,
                        "lastValueVisible": True
                    }
                })

            # 0. 분할 매수 타점 -> 노란색 점선 (style: 2), 4차는 찐손절 방어(주황색)
            for i, zone in enumerate(calc_res['zones']):
                title = f"{i+1}차 매수" if i < 3 else "4차(투매)"
                color = "#fff59d" if i < 3 else "#ffb74d"
                add_horizontal_line(float(zone['price']), color, 2, title)
                
            # 1. 기계적 진짜 손절선 -> 빨간색 실선 (style: 0)
            add_horizontal_line(float(calc_res['hard_stop_loss']), "#ef5350", 0, "찐 손절")
            
            # 2. 채널 기준선 (상/하단) -> 하얀색 실선 계열
            add_horizontal_line(float(channel_top), "#ffffff", 0, "채널 상단")
            add_horizontal_line(float(channel_bot), "#ffffff", 0, "채널 하단")
            
            # 3. 예상 평단가 -> 파란색 점선 (style: 2)
            add_horizontal_line(float(calc_res['avg_price']), "#2962ff", 2, "평단")
            
            # 4. 목표가 (초록색 실선 style: 0)
            for rr_label, price in rr_targets.items():
                add_horizontal_line(float(price), "#26a69a", 0, f"{rr_label}배")
            
            # 차트 테마 (트레이딩뷰 다크모드) 및 높이 설정
            chartOptions = {
                "height": 650, # 차트 세로 길이를 웅장하게 확장 (기본값 약 400)
                "layout": { "textColor": '#d1d4dc', "background": { "type": 'solid', "color": '#131722' } },
                "grid": {
                    "vertLines": { "color": 'rgba(42, 46, 57, 0)' },
                    "horzLines": { "color": 'rgba(42, 46, 57, 0.6)' }
                },
                "crosshair": { "mode": 0 },
                "timeScale": { "borderColor": 'rgba(197, 203, 206, 0.8)', "rightOffset": 20 }
            }

            # 차트 렌더링 호출
            renderLightweightCharts([{"chart": chartOptions, "series": seriesCandlestickChart}], key='candlestick')
            
            # 산술 결과 텍스트 안내 영역
            st.info(f"💡 **분석 결과 (비상금 포함 예측):**\n 1~3차까진 설정하신 예산 **{int(calc_res['base_budget']):,}원** 내에서 100% 매수됩니다.\n 만약 투매가 떨어져 비상용 4차 매수까지 강제 발동되면, 총 **{int(calc_res['total_spent']):,}원**이 투입되며 4차 포함 최종 평단가는 **{int(calc_res['avg_price']):,}원**입니다.\n 찐 손절선 이탈로 장사 접을 시 총 타격은 **{calc_res['loss_pct']:.2f}%** 입니다.")
            
            st.divider()
            st.markdown("#### 🎯 타점 도달 필요 하락률 (현재가 대비)")
            metric_cols = st.columns(4)
            for i, zone in enumerate(calc_res['zones']):
                drop_pct = ((zone['price'] / curr_price) - 1) * 100
                label = f"{i+1}차 진입 대기" if i < 3 else "4차 방어선 대기"
                metric_cols[i].metric(
                    label=label, 
                    value=f"{int(zone['price']):,} 원", 
                    delta=f"{drop_pct:.2f}%"
                )
            
        except ValueError as e:
            st.error(f"입력 오류: {e}")
    else:
        st.error("데이터를 불러오지 못했습니다. API 연결을 확인해주세요.")
