import streamlit as st
from concurrent.futures import ThreadPoolExecutor
from data_loader import StockDataLoader

@st.cache_data(ttl=30)
def _cached_price(code):
    return StockDataLoader.get_current_price(code)

def render_sidebar():
    with st.sidebar:
        st.title("📈 시각화 봇 V2")
        st.divider()
        
        # 웹소켓 상태 표시 (사이드바 상단 - 접기 기능 추가)
        with st.expander("🌐 시스템 상태", expanded=False):
            status_container = st.empty()
        
        st.divider()
        
        # 🔍 종목 코드 조회기 추가 (통합 검색 엔진)
        st.markdown("#### 🔍 종목 통합 검색")
        lookup_name = st.text_input("종목명 또는 티커 입력", placeholder="예: 삼성전자, AAPL", key="lookup_input", label_visibility="collapsed")
        
        if lookup_name.strip():
            # 네이버 검색 API 호출 (국내/해외 통합)
            lookup_results_raw = StockDataLoader.search_stock_naver(lookup_name.strip())
            
            if lookup_results_raw:
                for item in lookup_results_raw[:5]:
                    name = item['name']
                    symbol = item['symbol']
                    
                    # 시장 타입 판별
                    is_o = not symbol.isdigit() or len(symbol) != 6
                    m_type = "US" if is_o else "KR"
                    flag = "🇺🇸" if is_o else "🇰🇷"
                    
                    c1, c2 = st.columns([8, 2])
                    c1.markdown(f"{flag} `{name}` : **{symbol}**")
                    if c2.button("⭐", key=f"add_wl_{symbol}"):
                        from supabase_db import SupabaseDB
                        SupabaseDB.insert_watchlist(symbol, name, m_type)
                        st.success(f"{name} 추가됨")
                        st.rerun()
            else:
                st.markdown("<span style='color: #ef5350; font-size: 0.8rem;'>조회 결과 없음</span>", unsafe_allow_html=True)
                
        st.divider()

        # ⭐ 관심 종목 리스트 테이블
        st.markdown("#### ⭐ 관심 종목")
        
        # 🟢 필터 라디오 버튼 추가 (기본값: 국내)
        filter_type = st.radio(
            "분류", 
            ["전체", "🇰🇷 국내", "🇺🇸 해외"], 
            index=1, # "🇰🇷 국내"를 기본값으로 설정
            horizontal=True, 
            key="wl_filter",
            label_visibility="collapsed"
        )
        
        from supabase_db import SupabaseDB
        if SupabaseDB.is_connected():
            watchlist_all = SupabaseDB.fetch_watchlist()
            
            # 필터링 로직
            if filter_type == "🇰🇷 국내":
                watchlist = [s for s in watchlist_all if s['market_type'] == "KR"]
            elif filter_type == "🇺🇸 해외":
                watchlist = [s for s in watchlist_all if s['market_type'] == "US"]
            else:
                watchlist = watchlist_all

            if not watchlist:
                st.info("해당되는 종목이 없습니다.")
            else:
                # 사이드바 전용 스타일 (폰트 대폭 축소)
                st.markdown("""
                    <style>
                    .small-font { font-size: 0.65rem !important; color: #d1d4dc; }
                    .stButton button { 
                        padding: 1px 4px !important; 
                        font-size: 0.65rem !important; 
                        min-height: 20px !important;
                        line-height: 1 !important;
                    }
                    </style>
                """, unsafe_allow_html=True)
                
                # 헤더
                h_cols = st.columns([1, 4, 3, 1])
                h_cols[1].markdown("<div class='small-font' style='color:#888;'>종목</div>", unsafe_allow_html=True)
                h_cols[2].markdown("<div class='small-font' style='color:#888;'>가격</div>", unsafe_allow_html=True)

                codes = [s['stock_code'] for s in watchlist]
                with ThreadPoolExecutor(max_workers=len(codes)) as ex:
                    price_map = dict(zip(codes, ex.map(_cached_price, codes)))

                for stock in watchlist:
                    code = stock['stock_code']
                    name = stock['stock_name']
                    m_type = stock['market_type']
                    flag = "🇰🇷" if m_type == "KR" else "🇺🇸"

                    curr_p = price_map.get(code)
                    if curr_p:
                        price_str = f"{curr_p:,.2f}" if m_type == "US" else f"{int(curr_p):,}"
                    else:
                        price_str = "-"

                    r_cols = st.columns([1, 4, 3, 1])
                    r_cols[0].write(flag)
                    r_cols[1].markdown(f"<div class='small-font' style='color:#000;font-weight:600;'>{name}<br><code style='font-size:0.6rem;color:#000;'>{code}</code></div>", unsafe_allow_html=True)
                    r_cols[2].markdown(f"<div class='small-font' style='color:#000;font-weight:600;'>{price_str}</div>", unsafe_allow_html=True)

                    if r_cols[3].button("❌", key=f"del_wl_{code}"):
                        SupabaseDB.delete_watchlist(code)
                        st.rerun()
        
        st.divider()
        
    return status_container
