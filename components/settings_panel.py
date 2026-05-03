import streamlit as st

def render_settings_panel(c_price):
    st.markdown("<div style='font-size: 0.95rem; font-weight: bold; margin-bottom: 10px; color: #3498DB;'>⚙️ 전략 시뮬레이션</div>", unsafe_allow_html=True)
    
    is_overseas = st.session_state.get("is_overseas", False)
    unit = st.session_state.get("unit", "원")
    
    # 기본값 및 스텝 설정
    def_budget = 2000.0 if is_overseas else 3000000.0
    budget_step = 100.0 if is_overseas else 100000.0
    price_step = 0.1 if is_overseas else 100.0

    # --- 중기 전략 ---
    with st.expander("📊 중기: 채널 내 분할매수", expanded=True):
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
        
        st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 10px; color: #3498DB;'>📏 채널 범위 설정</div>", unsafe_allow_html=True)
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if "ct_input" not in st.session_state:
                st.session_state.ct_input = float(c_price) if is_overseas else int(c_price)
            channel_top = st.number_input(f"상단(저항) {unit}", step=price_step, key="ct_input")
            st.session_state.ch_top = channel_top
        with col_c2:
            if "cb_input" not in st.session_state:
                st.session_state.cb_input = float(c_price * 0.90) if is_overseas else int(c_price * 0.90)
            channel_bot = st.number_input(f"하단(지지) {unit}", step=price_step, key="cb_input")
            st.session_state.ch_bot = channel_bot
            
        hard_sl = channel_bot * 0.96
        if not is_overseas: hard_sl = int(hard_sl)
        
        col_h1, col_h2 = st.columns([6, 4])
        with col_h1:
            st.markdown(f"<p style='font-size: 0.85rem; color: #d1d4dc; margin-top: 2px; margin-bottom: 0;'>최종 손절선 (-4%)</p>", unsafe_allow_html=True)
        with col_h2:
            fmt_sl = f"{hard_sl:,.2f}" if is_overseas else f"{int(hard_sl):,}"
            st.markdown(f"<p style='font-size: 0.95rem; font-weight: bold; text-align: right; margin-top: 2px; margin-bottom: 0;'>{fmt_sl} {unit}</p>", unsafe_allow_html=True)
            
        st.markdown("<hr style='margin: 10px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)
        
        st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 10px; color: #3498DB;'>💰 진입 금액 및 비중</div>", unsafe_allow_html=True)
        
        col_b1, col_b2 = st.columns([4, 6])
        with col_b1:
            st.markdown("<p style='font-size: 0.85rem; font-weight: bold; margin-top: 5px; margin-bottom: 0;'>투입 금액</p>", unsafe_allow_html=True)
        with col_b2:
            total_budget = st.number_input(f"총 투입 예산({unit})", value=def_budget, step=budget_step, label_visibility="collapsed", key="budget_input")
            
        col_w1, col_w2, col_w3, col_w4 = st.columns(4)
        with col_w1: w1 = st.number_input("1차", 0, 100, 3, key="w1_input")
        with col_w2: w2 = st.number_input("2차", 0, 100, 3, key="w2_input")
        with col_w3: w3 = st.number_input("3차", 0, 100, 3, key="w3_input")
        with col_w4: w4 = st.number_input("4차", 0, 100, 0, key="w4_input")
        
        weights = [float(w1), float(w2), float(w3), float(w4)]

    # --- 단기 전략 ---
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
            st.session_state.resist_input = float(c_price) if is_overseas else int(c_price)
            
        resist_price = st.number_input(f"저항선 가격 ({unit})", step=price_step, key="resist_input", label_visibility="collapsed")
        
        st.markdown("<hr style='margin: 10px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 10px; color: #E74C3C;'>💰 단기 투자 예산 및 비중</div>", unsafe_allow_html=True)
        
        col_st_b1, col_st_b2 = st.columns([4, 6])
        with col_st_b1:
            st.markdown("<p style='font-size: 0.85rem; font-weight: bold; margin-top: 5px; margin-bottom: 0;'>투입 금액</p>", unsafe_allow_html=True)
        with col_st_b2:
            st_budget = st.number_input(f"단기 예산({unit})", value=def_budget, step=budget_step, label_visibility="collapsed", key="st_budget_input")
            
        st.markdown("<p style='font-size: 0.8rem; color: #d1d4dc; margin-top: 8px; margin-bottom: 2px;'>1~4차 진입 비중</p>", unsafe_allow_html=True)
        
        col_stw1, col_stw2, col_stw3, col_stw4 = st.columns(4)
        with col_stw1: st_w1 = st.number_input("1차 비중", 0, 100, 1, key="st_w1_input", label_visibility="collapsed")
        with col_stw2: st_w2 = st.number_input("2차 비중", 0, 100, 1, key="st_w2_input", label_visibility="collapsed")
        with col_stw3: st_w3 = st.number_input("3차 비중", 0, 100, 1, key="st_w3_input", label_visibility="collapsed")
        with col_stw4: st_w4 = st.number_input("4차 비중", 0, 100, 1, key="st_w4_input", label_visibility="collapsed")
        
        st_weights = [float(st_w1), float(st_w2), float(st_w3), float(st_w4)]

    with st.expander("장기: 조정 시 매집", expanded=False):
        st.markdown("<p style='font-size: 0.8rem; color: #d1d4dc;'>차트 보조선 출력 및 개별 파라미터 설정 예정 공간</p>", unsafe_allow_html=True)
        
    return {
        "mid_term": {
            "show_lines": show_lines_user,
            "rr_targets": rr_targets_sel,
            "channel_top": channel_top,
            "channel_bot": channel_bot,
            "hard_sl": hard_sl,
            "budget": total_budget,
            "weights": weights
        },
        "short_term": {
            "show_lines": show_lines_short,
            "rr_targets": st_rr_targets_sel,
            "resist_price": resist_price,
            "budget": st_budget,
            "weights": st_weights
        }
    }
