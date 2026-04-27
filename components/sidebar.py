import streamlit as st
from data_loader import StockDataLoader

def render_sidebar():
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
        
    return placeholder_summary
