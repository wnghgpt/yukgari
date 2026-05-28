import streamlit as st
from datetime import datetime
from calculator import StrategyCalculator

ST_WEIGHTS = [70, 30]

def render_settings_panel(c_price, symbol=None, name=None):
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        is_overseas = st.session_state.get("is_overseas", False)
        unit = st.session_state.get("unit", "원")
        price_step = 0.1 if is_overseas else 100.0

        def fmt_p(val):
            return f"{val:,.2f}" if is_overseas else f"{int(val):,}"

        # ── 총액 / 비중 (탭 위 공통) ──────────────────────────────
        col_a1, col_a2, col_a3 = st.columns([4, 2, 4])
        with col_a1:
            def_asset = 500.0 if is_overseas else 50000000.0
            asset_step = 10.0 if is_overseas else 1000000.0
            total_asset = st.number_input(f"총액({unit})", value=def_asset, step=asset_step, key="total_asset_input", label_visibility="collapsed")
        with col_a2:
            risk_pct = st.number_input("비중%", value=0.4, step=0.05, min_value=0.0, key="risk_pct_input", label_visibility="collapsed")
        with col_a3:
            allowed_loss = total_asset * risk_pct / 100
            loss_disp = f"${allowed_loss:,.1f}" if is_overseas else f"{allowed_loss/10000:.1f}만원"
            st.markdown(f"<p style='font-size: 0.78rem; color: #ef5350; margin-top: 8px;'>허용손실 {loss_disp}</p>", unsafe_allow_html=True)

        st.markdown("<p style='font-size: 0.7rem; color: #555e6e; margin-top: 2px; margin-bottom: 0;'>10% 예수금, 종목 15개 이내 유지.</p>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 8px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)

        calc_res = None
        rr_targets = None
        st_avg_price = 0
        st_hard_sl = 0
        st_prices = []
        st_alloc = []
        st_loss = 0
        mid_budget = 0
        st_budget = 0

        st.markdown("""
        <style>
        .stCheckbox label p {
            font-size: 0.7rem !important;
            white-space: nowrap !important;
            color: #d1d4dc !important;
        }
        </style>
        """, unsafe_allow_html=True)

        tab_short, tab_mid, tab_long = st.tabs(["⚡ 돌파", "📊 풀백/눌림목", "🛡️ 장기"])

        # ── 중기 전략 ──────────────────────────────────────────
        with tab_mid:
            col_mid_title, col_chk1, col_chk2 = st.columns([6, 2, 2])
            with col_mid_title:
                st.markdown("<div style='font-size: 0.85rem; font-weight: bold; color: #3498DB;'>목표가 표시</div>", unsafe_allow_html=True)
            with col_chk1:
                if "show_user_lines" not in st.session_state:
                    st.session_state.show_user_lines = True
                show_lines_user = st.checkbox("보조선", key="show_user_lines")
            with col_chk2:
                use_target = st.checkbox("목표가", key="use_target_input")

            if use_target:
                if "rr_target_input" not in st.session_state:
                    ct_prev = st.session_state.get("ct_input", float(c_price) if is_overseas else int(c_price))
                    cb_prev = st.session_state.get("cb_input", float(c_price * 0.90) if is_overseas else int(c_price * 0.90))
                    sl_pct_prev = st.session_state.get("mid_hsl_pct_input", 4.0)
                    if cb_prev > 0:
                        width_prev = (ct_prev - cb_prev) / cb_prev * 100
                        avg_prev = cb_prev * 0.767 + ct_prev * 0.233 if width_prev < 8 else cb_prev * 0.675 + ct_prev * 0.325
                        sl_prev = cb_prev * (1 - sl_pct_prev / 100)
                        default_target = avg_prev + 3.0 * (avg_prev - sl_prev)
                    else:
                        default_target = float(c_price * 1.30)
                    st.session_state.rr_target_input = float(default_target)
                rr_target_price = st.number_input(f"목표가 ({unit})", step=price_step, key="rr_target_input", label_visibility="collapsed")
            else:
                rr_target_price = 0.0

            st.markdown("<hr style='margin: 10px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 6px; color: #3498DB;'>📏 가격 범위 설정</div>", unsafe_allow_html=True)

            channel_bot_prev = st.session_state.get("cb_input", float(c_price * 0.90) if is_overseas else int(c_price * 0.90))
            if use_target and rr_target_price > 0 and channel_bot_prev > 0:
                sl_pct = st.session_state.get("mid_hsl_pct_input", 4.0)
                stop_loss_tmp = channel_bot_prev * (1 - sl_pct / 100)
                avg_target = (rr_target_price + 3.0 * stop_loss_tmp) / 4.0
                top_est3 = (avg_target - 0.767 * channel_bot_prev) / 0.233
                width_est3 = (top_est3 - channel_bot_prev) / channel_bot_prev * 100
                channel_top_calc = top_est3 if width_est3 <= 10 else (avg_target - 0.675 * channel_bot_prev) / 0.325
                channel_top_calc = float(channel_top_calc)
                if not is_overseas:
                    channel_top_calc = int(channel_top_calc)
                st.session_state.ct_input = channel_top_calc
            else:
                if "ct_input" not in st.session_state:
                    st.session_state.ct_input = float(c_price) if is_overseas else int(c_price)

            col_lbl_ct, col_ct = st.columns([3, 7])
            with col_lbl_ct:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>저항선</p>", unsafe_allow_html=True)
            with col_ct:
                channel_top = st.number_input(f"채널 상단({unit})", step=price_step, key="ct_input", disabled=(use_target and rr_target_price > 0), label_visibility="collapsed")
            st.session_state.ch_top = channel_top

            # Auto-sync 저항선→지지선 (목표가 역산 모드일 때는 제외)
            if not (use_target and rr_target_price > 0):
                ct_prev = st.session_state.get("ct_input_prev")
                if ct_prev is not None and channel_top != ct_prev:
                    if st.session_state.get("cb_input") == ct_prev:
                        st.session_state["cb_input"] = channel_top
                st.session_state["ct_input_prev"] = channel_top

            if "cb_input" not in st.session_state:
                st.session_state.cb_input = float(c_price * 0.90) if is_overseas else int(c_price * 0.90)

            col_lbl_cb, col_cb = st.columns([3, 7])
            with col_lbl_cb:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>지지선</p>", unsafe_allow_html=True)
            with col_cb:
                channel_bot = st.number_input(f"채널 하단({unit})", step=price_step, key="cb_input", label_visibility="collapsed")
            st.session_state.ch_bot = channel_bot

            width_pct = (channel_top - channel_bot) / channel_bot * 100 if channel_top > channel_bot > 0 else 0

            col_lbl_gap, col_gap_val, col_lbl_sl, col_sl_pct, col_sl_sign = st.columns([2, 4, 2, 2, 1])
            with col_lbl_gap:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>갭</p>", unsafe_allow_html=True)
            with col_gap_val:
                if width_pct > 10:
                    st.markdown(f"<p style='font-size: 0.75rem; margin-top: 8px; color: #ef5350;'><b>{width_pct:.1f}%</b></p>", unsafe_allow_html=True)
                elif width_pct > 0:
                    st.markdown(f"<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>{width_pct:.1f}%</p>", unsafe_allow_html=True)
            with col_lbl_sl:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px; text-align: center;'>손절</p>", unsafe_allow_html=True)
            with col_sl_pct:
                mid_hard_sl_pct = st.number_input("손절(%)", 0.0, 30.0, 4.0, step=0.1, key="mid_hsl_pct_input", label_visibility="collapsed")
            with col_sl_sign:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>%</p>", unsafe_allow_html=True)

            hard_sl = channel_bot * (1 - mid_hard_sl_pct / 100)
            if not is_overseas: hard_sl = int(hard_sl)

            if width_pct > 0:
                w_str = "20 / 30 / 50" if width_pct <= 10 else "15 / 25 / 35 / 25"
                st.markdown(f"<p style='font-size: 0.7rem; color: #8a8d9a; margin-top: 2px; margin-bottom: 0;'>비중: {w_str}</p>", unsafe_allow_html=True)

            # ── 시뮬레이션 결과 ──
            st.markdown("<hr style='margin: 12px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 6px; color: #3498DB;'>* 전략 요약</div>", unsafe_allow_html=True)
            try:
                _dummy = StrategyCalculator.calculate_pyramid(
                    channel_top=float(channel_top),
                    channel_bot=float(channel_bot),
                    hard_stop_loss=float(hard_sl),
                    base_budget=1_000_000,
                )
                mid_loss_pct = _dummy['loss_pct']
                mid_budget = (allowed_loss / (mid_loss_pct / 100)) if mid_loss_pct > 0 else 0

                calc_res = StrategyCalculator.calculate_pyramid(
                    channel_top=float(channel_top),
                    channel_bot=float(channel_bot),
                    hard_stop_loss=float(hard_sl),
                    base_budget=float(mid_budget),
                )
                rr_targets = StrategyCalculator.calculate_rr_targets(
                    avg_price=calc_res['avg_price'],
                    hard_stop_loss=calc_res['hard_stop_loss'],
                    rr_multipliers=[3, 5]
                )
                steps = calc_res.get("steps", 4)
                mid_rr3 = calc_res['avg_price'] + 3 * (calc_res['avg_price'] - calc_res['hard_stop_loss'])
                mid_budget_str = f"${mid_budget:,.0f}" if is_overseas else f"{mid_budget/10000:.0f}만원"

                st.markdown(f"""
                    <div style='font-size: 0.78rem; line-height: 1.8; margin-bottom: 10px; text-align: center;'>
                        <b>평단</b> {fmt_p(calc_res['avg_price'])}{unit} | <span style='color:#ef5350;'><b>손실율 {mid_loss_pct:.2f}%</b></span> | 투입 {mid_budget_str} ({int(calc_res['total_qty']):,}주)
                    </div>
                """, unsafe_allow_html=True)

                for i, zone in enumerate(calc_res['zones']):
                    drop_pct = ((zone['price'] / c_price) - 1) * 100
                    color_pct = "#2ecc71" if drop_pct >= 0 else "#ef5350"
                    amt_val = zone['allocate_amt'] / 10000 if not is_overseas else zone['allocate_amt']
                    amt_unit = "만" if not is_overseas else ""
                    st.markdown(f"""
                        <div style='font-size: 0.65rem; display: flex; justify-content: space-between; margin-bottom: 2px;'>
                            <span><b>{i+1}차:</b> {fmt_p(zone['price'])}{unit} <span style='color:{color_pct};'>({drop_pct:+.1f}%)</span></span>
                            <span style='color:#8a8d9a;'>{int(zone['qty']):,}주 ({amt_val:.1f}{amt_unit})</span>
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown(f"""
                    <div style='font-size: 0.75rem; color:#ef5350; display:flex; justify-content:space-between; margin-top:4px;'>
                        <b>손절 (-{mid_hard_sl_pct:.1f}%):</b><b>{fmt_p(calc_res['hard_stop_loss'])}{unit}</b>
                    </div>
                    <div style='font-size: 0.75rem; color:#2ecc71; display:flex; justify-content:space-between; margin-top:2px;'>
                        <b>목표가 (RR 3x):</b><b>{fmt_p(mid_rr3)}{unit}</b>
                    </div>
                """, unsafe_allow_html=True)

                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                if symbol and st.button("📒 일지에 추가", width="stretch", key="btn_journal_mid"):
                    from datetime import date as _date
                    from components.trade_journal import quick_add_journal
                    weight_list = [20, 30, 50] if steps == 3 else [15, 25, 35, 25]
                    payload = {
                        "date": str(_date.today()),
                        "ticker": name,
                        "result": "감시",
                        "channel_top": float(channel_top),
                        "channel_bottom": float(channel_bot),
                        "stages": steps,
                        "stop_loss": float(calc_res['hard_stop_loss']),
                        "target_price": float(mid_rr3),
                    }
                    for i, zone in enumerate(calc_res['zones']):
                        payload[f"entry{i+1}_price"] = float(zone['price'])
                        payload[f"entry{i+1}_weight"] = int(zone['qty'])
                    quick_add_journal(payload)

            except Exception as e:
                st.caption(f"시뮬레이션 오류: {e}")

        # ── 단기 전략 ──────────────────────────────────────────
        with tab_short:
            col_st_title, col_st_chk = st.columns([7, 3])
            with col_st_title:
                st.markdown("<div style='font-size: 0.85rem; font-weight: bold; color: #3498DB;'>목표가 표시</div>", unsafe_allow_html=True)
            with col_st_chk:
                if "show_short_lines" not in st.session_state:
                    st.session_state.show_short_lines = False
                show_lines_short = st.checkbox("보조선", key="show_short_lines")

            st.markdown("<hr style='margin: 10px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 6px; color: #3498DB;'>📏 가격 범위 설정</div>", unsafe_allow_html=True)

            col_lbl1, col_p1, col_l1, col_pct1, col_sign1 = st.columns([2, 4, 2, 2, 1])
            with col_lbl1:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>저항선</p>", unsafe_allow_html=True)
            with col_p1:
                if "resist_input" not in st.session_state:
                    st.session_state.resist_input = float(c_price) if is_overseas else int(c_price)
                resist_price = st.number_input(f"저항선({unit})", step=price_step, key="resist_input", label_visibility="collapsed")
            with col_l1:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px; text-align: center;'>1차</p>", unsafe_allow_html=True)
            with col_pct1:
                st_entry1_pct = st.number_input("1차%", 0.0, 20.0, 2.0, step=0.1, key="st_entry1_pct_input", label_visibility="collapsed")
            with col_sign1:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>%</p>", unsafe_allow_html=True)

            # Auto-sync 저항선→지지선
            rp_prev = st.session_state.get("resist_input_prev")
            if rp_prev is not None and resist_price != rp_prev:
                if st.session_state.get("support_input") == rp_prev:
                    st.session_state["support_input"] = resist_price
            st.session_state["resist_input_prev"] = resist_price

            col_lbl2, col_p2, col_l2, col_pct2, col_sign2 = st.columns([2, 4, 2, 2, 1])
            with col_lbl2:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>지지선</p>", unsafe_allow_html=True)
            with col_p2:
                if "support_input" not in st.session_state:
                    st.session_state.support_input = float(c_price) if is_overseas else int(c_price)
                support_price = st.number_input(f"지지선({unit})", step=price_step, key="support_input", label_visibility="collapsed")
            with col_l2:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px; text-align: center;'>2차</p>", unsafe_allow_html=True)
            with col_pct2:
                st_entry2_pct = st.number_input("2차%", 0.0, 20.0, 1.0, step=0.1, key="st_entry2_pct_input", label_visibility="collapsed")
            with col_sign2:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>%</p>", unsafe_allow_html=True)

            col_lbl3, col_p3, col_l3, col_pct3, col_sign3 = st.columns([2, 4, 2, 2, 1])
            with col_lbl3:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>갭</p>", unsafe_allow_html=True)
            with col_p3:
                if resist_price > 0 and support_price > 0:
                    gap_pct = abs(resist_price - support_price) / support_price * 100
                    if gap_pct > 2:
                        st.markdown(f"<p style='font-size: 0.75rem; margin-top: 8px; color: #ef5350;'>주의! <b>{gap_pct:.1f}%</b></p>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>{gap_pct:.1f}%</p>", unsafe_allow_html=True)
            with col_l3:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px; text-align: center;'>손절</p>", unsafe_allow_html=True)
            with col_pct3:
                st_sl_pct = st.number_input("손절%", 0.0, 30.0, 4.0, step=0.1, key="st_sl_pct_input", label_visibility="collapsed")
            with col_sign3:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>%</p>", unsafe_allow_html=True)

            st.markdown("<p style='font-size: 0.7rem; color: #8a8d9a; margin-top: 2px; margin-bottom: 0;'>비중: 70 / 30</p>", unsafe_allow_html=True)

            # ── 시뮬레이션 결과 ──
            st.markdown("<hr style='margin: 12px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 6px; color: #3498DB;'>* 전략 요약</div>", unsafe_allow_html=True)
            if resist_price > 0:
                try:
                    e1_p = resist_price * (1 + st_entry1_pct / 100)
                    e2_p = support_price * (1 + st_entry2_pct / 100) if support_price > 0 else resist_price * (1 + st_entry2_pct / 100)
                    st_prices = [e1_p, e2_p]
                    _dummy_alloc = [(w / 100) * 1_000_000 for w in ST_WEIGHTS]
                    st_avg_price = sum(p * a for p, a in zip(st_prices, _dummy_alloc)) / 1_000_000
                    st_hard_sl = support_price * (1 - st_sl_pct / 100) if support_price > 0 else resist_price * (1 - st_sl_pct / 100)
                    st_loss_pct = (st_avg_price - st_hard_sl) / st_avg_price * 100 if st_avg_price > 0 else 0
                    st_budget = (allowed_loss / (st_loss_pct / 100)) if st_loss_pct > 0 else 0
                    st_alloc = [(w / 100) * st_budget for w in ST_WEIGHTS]
                    st_loss = st_budget * (st_loss_pct / 100)
                    st_rr3 = st_avg_price + 3 * (st_avg_price - st_hard_sl)
                    st_budget_str = f"${st_budget:,.0f}" if is_overseas else f"{st_budget/10000:.0f}만원"

                    st.markdown(f"""
                        <div style='font-size: 0.78rem; line-height: 1.8; margin-bottom: 10px; text-align: center;'>
                            <b>평단</b> {fmt_p(st_avg_price)}{unit} | <span style='color:#ef5350;'><b>손실율 {st_loss_pct:.2f}%</b></span> | 투입 {st_budget_str} ({int(st_budget / st_avg_price):,}주)
                        </div>
                    """, unsafe_allow_html=True)

                    ref_labels = [f"저항선+{st_entry1_pct:.1f}%", f"지지선+{st_entry2_pct:.1f}%"]
                    for i, (p, w) in enumerate(zip(st_prices, ST_WEIGHTS)):
                        amt = st_alloc[i]
                        qty = int(amt / p) if p > 0 else 0
                        amt_val = amt / 10000 if not is_overseas else amt
                        amt_unit = "만" if not is_overseas else ""
                        drop_pct = ((p / c_price) - 1) * 100
                        color_pct = "#2ecc71" if drop_pct >= 0 else "#ef5350"
                        st.markdown(f"""
                            <div style='font-size: 0.65rem; display: flex; justify-content: space-between; margin-bottom: 2px;'>
                                <span><b>{i+1}차:</b> {fmt_p(p)}{unit} <span style='color:{color_pct};'>({drop_pct:+.1f}%)</span></span>
                                <span style='color:#8a8d9a;'>{qty}주 ({amt_val:.1f}{amt_unit})</span>
                            </div>
                        """, unsafe_allow_html=True)

                    st.markdown(f"""
                        <div style='font-size: 0.75rem; color:#ef5350; display:flex; justify-content:space-between; margin-top:4px;'>
                            <b>손절 (지지선-{st_sl_pct:.1f}%):</b><b>{fmt_p(st_hard_sl)}{unit}</b>
                        </div>
                        <div style='font-size: 0.75rem; color:#2ecc71; display:flex; justify-content:space-between; margin-top:2px;'>
                            <b>목표가 (RR 3x):</b><b>{fmt_p(st_rr3)}{unit}</b>
                        </div>
                    """, unsafe_allow_html=True)

                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    if symbol and st.button("📒 일지에 추가", width="stretch", key="btn_journal_short"):
                        from datetime import date as _date
                        from components.trade_journal import quick_add_journal
                        payload = {
                            "date": str(_date.today()),
                            "ticker": name,
                            "result": "감시",
                            "channel_top": float(resist_price),
                            "channel_bottom": float(support_price) if support_price > 0 else None,
                            "stages": 2,
                            "entry1_price": float(st_prices[0]),
                            "entry1_weight": int(st_alloc[0] / st_prices[0]) if st_prices[0] > 0 else 0,
                            "entry2_price": float(st_prices[1]),
                            "entry2_weight": int(st_alloc[1] / st_prices[1]) if st_prices[1] > 0 else 0,
                            "stop_loss": float(st_hard_sl),
                            "target_price": float(st_rr3),
                        }
                        quick_add_journal(payload)
                except Exception as e:
                    st.caption(f"시뮬레이션 오류: {e}")
            else:
                st.caption("저항선을 입력하면 시뮬레이션이 표시됩니다.")

        # ── 장기 전략 ──────────────────────────────────────────
        with tab_long:
            st.markdown("<p style='font-size: 0.8rem; color: #d1d4dc;'>준비 중</p>", unsafe_allow_html=True)

        return {
            "mid_term": {
                "show_lines": show_lines_user,
                "rr_targets": [3, 5],
                "channel_top": channel_top,
                "channel_bot": channel_bot,
                "hard_sl": hard_sl,
                "hard_sl_pct": mid_hard_sl_pct,
                "budget": mid_budget,
            },
            "short_term": {
                "show_lines": show_lines_short,
                "rr_targets": [3, 5],
                "resist_price": resist_price,
                "support_price": support_price,
                "entry1_pct": st_entry1_pct,
                "entry2_pct": st_entry2_pct,
                "hard_sl_pct": st_sl_pct,
                "budget": st_budget,
            },
            "calc_res": calc_res,
            "rr_targets": rr_targets,
            "st_avg_price": st_avg_price,
            "st_hard_sl": st_hard_sl,
            "st_prices": st_prices,
            "st_alloc": st_alloc,
            "st_loss": st_loss,
        }
