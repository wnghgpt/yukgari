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

        st.markdown("""
        <style>
        .stCheckbox label p {
            font-size: 0.7rem !important;
            white-space: nowrap !important;
            color: #d1d4dc !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # ── 피라미딩 탭 헬퍼 ───────────────────────────────────────
        def _pyramid_tab(key, default_sl_pct, show_key):
            ct_key     = f"ct_input_{key}"
            cb_key     = f"cb_input_{key}"
            sl_key     = f"hsl_pct_{key}"
            target_key = f"use_target_{key}"
            rr_key     = f"rr_target_{key}"
            prev_ct_key= f"ct_prev_{key}"

            col_title, col_chk1, col_chk2 = st.columns([6, 2, 2])
            with col_title:
                st.markdown("<div style='font-size: 0.85rem; font-weight: bold; color: #3498DB;'>목표가 표시</div>", unsafe_allow_html=True)
            with col_chk1:
                if show_key not in st.session_state:
                    st.session_state[show_key] = False
                show_lines = st.checkbox("보조선", key=show_key)
            with col_chk2:
                use_target = st.checkbox("목표가", key=target_key)

            if use_target:
                if rr_key not in st.session_state:
                    ct_p = st.session_state.get(ct_key, float(c_price) if is_overseas else int(c_price))
                    cb_p = st.session_state.get(cb_key, float(c_price * 0.90) if is_overseas else int(c_price * 0.90))
                    sl_p = st.session_state.get(sl_key, default_sl_pct)
                    if cb_p > 0:
                        w = (ct_p - cb_p) / cb_p * 100
                        avg_p = cb_p * 0.767 + ct_p * 0.233 if w < 8 else cb_p * 0.675 + ct_p * 0.325
                        sl_v  = cb_p * (1 - sl_p / 100)
                        default_target = avg_p + 3.0 * (avg_p - sl_v)
                    else:
                        default_target = float(c_price * 1.30)
                    st.session_state[rr_key] = float(default_target)
                rr_target_price = st.number_input(f"목표가 ({unit})", step=price_step, key=rr_key, label_visibility="collapsed")
            else:
                rr_target_price = 0.0

            st.markdown("<hr style='margin: 10px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 6px; color: #3498DB;'>📏 가격 범위 설정</div>", unsafe_allow_html=True)

            cb_prev = st.session_state.get(cb_key, float(c_price * 0.90) if is_overseas else int(c_price * 0.90))
            if use_target and rr_target_price > 0 and cb_prev > 0:
                sl_p = st.session_state.get(sl_key, default_sl_pct)
                stop_loss_tmp = cb_prev * (1 - sl_p / 100)
                avg_target = (rr_target_price + 3.0 * stop_loss_tmp) / 4.0
                top_est3 = (avg_target - 0.767 * cb_prev) / 0.233
                w_est = (top_est3 - cb_prev) / cb_prev * 100
                ct_calc = top_est3 if w_est <= 10 else (avg_target - 0.675 * cb_prev) / 0.325
                ct_calc = float(ct_calc) if is_overseas else int(ct_calc)
                st.session_state[ct_key] = ct_calc
            else:
                if ct_key not in st.session_state:
                    st.session_state[ct_key] = float(c_price) if is_overseas else int(c_price)

            col_lbl_ct, col_ct = st.columns([3, 7])
            with col_lbl_ct:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>저항선</p>", unsafe_allow_html=True)
            with col_ct:
                channel_top = st.number_input(f"채널 상단({unit})", step=price_step, key=ct_key,
                                              disabled=(use_target and rr_target_price > 0), label_visibility="collapsed")

            # Auto-sync 저항선→지지선
            if not (use_target and rr_target_price > 0):
                ct_prev_val = st.session_state.get(prev_ct_key)
                if ct_prev_val is not None and channel_top != ct_prev_val:
                    if st.session_state.get(cb_key) == ct_prev_val:
                        st.session_state[cb_key] = channel_top
                st.session_state[prev_ct_key] = channel_top

            if cb_key not in st.session_state:
                st.session_state[cb_key] = float(c_price * 0.90) if is_overseas else int(c_price * 0.90)

            col_lbl_cb, col_cb = st.columns([3, 7])
            with col_lbl_cb:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>지지선</p>", unsafe_allow_html=True)
            with col_cb:
                channel_bot = st.number_input(f"채널 하단({unit})", step=price_step, key=cb_key, label_visibility="collapsed")

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
                hard_sl_pct = st.number_input("손절(%)", 0.0, 30.0, default_sl_pct, step=0.1, key=sl_key, label_visibility="collapsed")
            with col_sl_sign:
                st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>%</p>", unsafe_allow_html=True)

            hard_sl = channel_bot * (1 - hard_sl_pct / 100)
            if not is_overseas: hard_sl = int(hard_sl)

            if width_pct > 0:
                w_str = "20 / 30 / 50" if width_pct <= 10 else "15 / 25 / 35 / 25"
                st.markdown(f"<p style='font-size: 0.7rem; color: #8a8d9a; margin-top: 2px; margin-bottom: 0;'>비중: {w_str}</p>", unsafe_allow_html=True)

            # ── 시뮬레이션 결과 ──
            st.markdown("<hr style='margin: 12px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 6px; color: #3498DB;'>* 전략 요약</div>", unsafe_allow_html=True)

            calc_res_l = None
            rr_targets_l = None
            budget_l = 0

            try:
                _dummy = StrategyCalculator.calculate_pyramid(
                    channel_top=float(channel_top), channel_bot=float(channel_bot),
                    hard_stop_loss=float(hard_sl), base_budget=1_000_000,
                )
                loss_pct = _dummy['loss_pct']
                budget_l = (allowed_loss / (loss_pct / 100)) if loss_pct > 0 else 0

                calc_res_l = StrategyCalculator.calculate_pyramid(
                    channel_top=float(channel_top), channel_bot=float(channel_bot),
                    hard_stop_loss=float(hard_sl), base_budget=float(budget_l),
                )
                rr_targets_l = StrategyCalculator.calculate_rr_targets(
                    avg_price=calc_res_l['avg_price'],
                    hard_stop_loss=calc_res_l['hard_stop_loss'],
                    rr_multipliers=[3, 5]
                )
                steps = calc_res_l.get("steps", 4)
                rr3 = calc_res_l['avg_price'] + 3 * (calc_res_l['avg_price'] - calc_res_l['hard_stop_loss'])
                budget_str = f"${budget_l:,.0f}" if is_overseas else f"{budget_l/10000:.0f}만원"

                st.markdown(f"""
                    <div style='font-size: 0.78rem; line-height: 1.8; margin-bottom: 10px; text-align: center;'>
                        <b>평단</b> {fmt_p(calc_res_l['avg_price'])}{unit} | <span style='color:#ef5350;'><b>손실율 {loss_pct:.2f}%</b></span> | 투입 {budget_str} ({int(calc_res_l['total_qty']):,}주)
                    </div>
                """, unsafe_allow_html=True)

                for i, zone in enumerate(calc_res_l['zones']):
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
                        <b>손절 (-{hard_sl_pct:.1f}%):</b><b>{fmt_p(calc_res_l['hard_stop_loss'])}{unit}</b>
                    </div>
                    <div style='font-size: 0.75rem; color:#2ecc71; display:flex; justify-content:space-between; margin-top:2px;'>
                        <b>목표가 (RR 3x):</b><b>{fmt_p(rr3)}{unit}</b>
                    </div>
                """, unsafe_allow_html=True)

                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                if symbol and st.button("📒 일지에 추가", width="stretch", key=f"btn_journal_{key}"):
                    from datetime import date as _date
                    from components.trade_journal import quick_add_journal
                    payload = {
                        "date": str(_date.today()), "ticker": name, "result": "감시",
                        "channel_top": float(channel_top), "channel_bottom": float(channel_bot),
                        "stages": steps, "stop_loss": float(calc_res_l['hard_stop_loss']),
                        "target_price": float(rr3),
                    }
                    for i, zone in enumerate(calc_res_l['zones']):
                        payload[f"entry{i+1}_price"] = float(zone['price'])
                        payload[f"entry{i+1}_weight"] = int(zone['qty'])
                    quick_add_journal(payload)

            except Exception as e:
                st.caption(f"시뮬레이션 오류: {e}")

            return {
                "show_lines": show_lines, "calc_res": calc_res_l, "rr_targets": rr_targets_l,
                "budget": budget_l, "channel_top": channel_top, "channel_bot": channel_bot,
                "hard_sl": hard_sl, "hard_sl_pct": hard_sl_pct,
            }

        # ── 돌파 탭 헬퍼 ───────────────────────────────────────────
        def _breakout_tab(key, show_key, default_sl_pct=4.0, missed_sl_pct=5.0, missed_logic="pullback", force_zone=False, rr_multiple=4):
            resist_key  = f"resist_input_{key}"
            sl_key      = f"st_sl_pct_{key}"
            missed_key  = f"missed_{key}"
            support_key = f"support_input_{key}"

            if not force_zone:
                col_title, col_chk, col_missed = st.columns([5, 2, 3])
                with col_title:
                    st.markdown("<div style='font-size: 0.85rem; font-weight: bold; color: #3498DB;'>목표가 표시</div>", unsafe_allow_html=True)
                with col_chk:
                    if show_key not in st.session_state:
                        st.session_state[show_key] = False
                    show_lines = st.checkbox("보조선", key=show_key)
                with col_missed:
                    missed = st.checkbox("돌파 놓침", key=missed_key)
            else:
                col_title, col_chk = st.columns([7, 3])
                with col_title:
                    st.markdown("<div style='font-size: 0.85rem; font-weight: bold; color: #3498DB;'>목표가 표시</div>", unsafe_allow_html=True)
                with col_chk:
                    if show_key not in st.session_state:
                        st.session_state[show_key] = False
                    show_lines = st.checkbox("보조선", key=show_key)
                missed = True

            st.markdown("<hr style='margin: 10px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 6px; color: #3498DB;'>📏 가격 범위 설정</div>", unsafe_allow_html=True)

            # zone 모드: force_zone이거나 missed=ON + zone logic
            is_zone = force_zone or (missed and missed_logic == "zone")

            if not is_zone:
                # ── 일반 모드: 저항선 + 손절% 한 줄 ──
                col_lbl1, col_p1, col_l1, col_pct1, col_sign1 = st.columns([2, 4, 2, 2, 1])
                with col_lbl1:
                    st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>저항선</p>", unsafe_allow_html=True)
                with col_p1:
                    if resist_key not in st.session_state:
                        st.session_state[resist_key] = float(c_price) if is_overseas else int(c_price)
                    resist_price = st.number_input(f"저항선({unit})", step=price_step, key=resist_key, label_visibility="collapsed")
                with col_l1:
                    st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px; text-align: center;'>손절</p>", unsafe_allow_html=True)
                with col_pct1:
                    st_sl_pct = st.number_input("손절%", 0.0, 30.0, default_sl_pct, step=0.1, key=sl_key, label_visibility="collapsed")
                with col_sign1:
                    st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>%</p>", unsafe_allow_html=True)
                support_price = 0.0
            else:
                # ── zone 모드: 저항선 / 지지선 동일 레이아웃 두 줄 ──
                st_sl_pct = missed_sl_pct
                col_lbl1, col_p1 = st.columns([2, 8])
                with col_lbl1:
                    st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>저항선</p>", unsafe_allow_html=True)
                with col_p1:
                    if resist_key not in st.session_state:
                        st.session_state[resist_key] = float(c_price) if is_overseas else int(c_price)
                    resist_price = st.number_input(f"저항선({unit})", step=price_step, key=resist_key, label_visibility="collapsed")
                col_lbl2, col_p2 = st.columns([2, 8])
                with col_lbl2:
                    st.markdown("<p style='font-size: 0.75rem; color: #8a8d9a; margin-top: 8px;'>지지선</p>", unsafe_allow_html=True)
                with col_p2:
                    if support_key not in st.session_state:
                        st.session_state[support_key] = float(c_price * 0.9) if is_overseas else int(c_price * 0.9)
                    support_price = st.number_input(f"지지선({unit})", step=price_step, key=support_key, label_visibility="collapsed")

            if not missed:
                weights = [70, 30]
            elif missed_logic == "zone":
                weights = [20, 30, 50]
            else:
                weights = [30, 40, 30]

            # ── 시뮬레이션 ──
            st.markdown("<hr style='margin: 12px 0; border-color: #2a2e39;'>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 0.85rem; font-weight: bold; margin-bottom: 6px; color: #3498DB;'>* 전략 요약</div>", unsafe_allow_html=True)

            avg_price_l = 0
            hard_sl_l   = 0
            prices_l    = []
            alloc_l     = []
            loss_l      = 0
            budget_l    = 0
            rr3_l       = 0

            if resist_price > 0:
                try:
                    if is_zone:
                        if support_price <= 0 or resist_price <= support_price:
                            st.caption("저항선 > 지지선 조건을 확인하세요.")
                            return {"show_lines": show_lines, "missed": missed,
                                    "resist_price": resist_price, "support_price": support_price,
                                    "hard_sl_pct": st_sl_pct, "budget": 0,
                                    "avg_price": 0, "hard_sl": 0, "prices": [], "alloc": [], "loss": 0}
                        rng = resist_price - support_price
                        prices_l = [resist_price - rng / 3, resist_price - rng * 2 / 3, support_price]
                        _dummy = [(w / 100) * 1_000_000 for w in weights]
                        avg_price_l = sum(p * a for p, a in zip(prices_l, _dummy)) / 1_000_000
                        hard_sl_l = avg_price_l * (1 - missed_sl_pct / 100)
                        if not is_overseas: hard_sl_l = int(hard_sl_l)
                        sl_label = f"평단-{missed_sl_pct:.0f}%"
                    else:
                        hard_sl_l = resist_price * (1 - st_sl_pct / 100)
                        if not is_overseas: hard_sl_l = int(hard_sl_l)
                        sl_label = f"저항선-{st_sl_pct:.1f}%"
                        if not missed:
                            prices_l = [resist_price * 1.02, resist_price * 0.98]
                        else:
                            prices_l = [resist_price * 1.04, resist_price * 1.01, resist_price * 0.98]
                        _dummy = [(w / 100) * 1_000_000 for w in weights]
                        avg_price_l = sum(p * a for p, a in zip(prices_l, _dummy)) / 1_000_000

                    loss_pct = (avg_price_l - hard_sl_l) / avg_price_l * 100 if avg_price_l > 0 else 0
                    budget_l = (allowed_loss / (loss_pct / 100)) if loss_pct > 0 else 0
                    alloc_l  = [(w / 100) * budget_l for w in weights]
                    loss_l   = budget_l * (loss_pct / 100)
                    rr3_l    = avg_price_l + rr_multiple * (avg_price_l - hard_sl_l)
                    budget_str = f"${budget_l:,.0f}" if is_overseas else f"{budget_l/10000:.0f}만원"

                    target_pct = 4 * loss_pct
                    if not missed:
                        buy_desc, ratio_desc = "저항선+2% 1차 / 저항선-2% 2차", "70:30"
                        sl_desc = f"저항선-{st_sl_pct:.0f}% 손절"
                    elif is_zone:
                        buy_desc, ratio_desc = "1/3점 / 2/3점 / 지지선", "20:30:50"
                        sl_desc = f"평단-{missed_sl_pct:.0f}% 손절"
                    else:
                        buy_desc, ratio_desc = "저항선+4% / +1% / -2%", "30:40:30"
                        sl_desc = f"저항선-{st_sl_pct:.0f}% 손절"
                    st.markdown(f"""
                        <div style='font-size: 0.72rem; color: #8a8d9a; margin-bottom: 2px;'>
                            <b style='color:#d1d4dc;'>매수:</b> {buy_desc} &nbsp;|&nbsp; 비중 {ratio_desc}
                        </div>
                        <div style='font-size: 0.72rem; color: #8a8d9a; margin-bottom: 6px;'>
                            <b style='color:#d1d4dc;'>매도:</b> <span style='color:#ef5350;'>{sl_desc}</span> &nbsp;|&nbsp; <span style='color:#2ecc71;'>평단+{target_pct:.0f}% 익절</span>
                        </div>
                        <div style='font-size: 0.78rem; line-height: 1.8; margin-bottom: 14px;'>
                            <b>평단:</b> {fmt_p(avg_price_l)}{unit} &nbsp;|&nbsp; <span style='color:#ef5350;'>손실률: {loss_pct:.2f}%</span> &nbsp;|&nbsp; 손익비: {rr_multiple}
                        </div>
                    """, unsafe_allow_html=True)

                    for i, (p, w) in enumerate(zip(prices_l, weights)):
                        amt = alloc_l[i]
                        qty = int(amt / p) if p > 0 else 0
                        amt_val = amt / 10000 if not is_overseas else amt
                        amt_unit = "만" if not is_overseas else ""
                        drop_pct = ((p / c_price) - 1) * 100
                        color_pct = "#2ecc71" if drop_pct >= 0 else "#ef5350"
                        st.markdown(f"""
                            <div style='font-size: 0.65rem; margin-bottom: 2px;'>
                                <b>{i+1}차:</b> {fmt_p(p)}{unit} <span style='color:{color_pct};'>({drop_pct:+.1f}%)</span>
                                &nbsp;&nbsp;<span style='color:#8a8d9a;'>{qty}주 ({amt_val:.1f}{amt_unit})</span>
                            </div>
                        """, unsafe_allow_html=True)

                    st.markdown(f"""
                        <div style='font-size: 0.75rem; color:#ef5350; margin-top:4px;'>
                            <b>손절:</b> {fmt_p(hard_sl_l)}{unit}
                        </div>
                        <div style='font-size: 0.75rem; color:#2ecc71; margin-top:2px;'>
                            <b>목표가:</b> {fmt_p(rr3_l)}{unit}
                        </div>
                    """, unsafe_allow_html=True)

                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    if symbol and st.button("📒 일지에 추가", width="stretch", key=f"btn_journal_{key}"):
                        from datetime import date as _date
                        from components.trade_journal import quick_add_journal
                        payload = {
                            "date": str(_date.today()), "ticker": name, "result": "감시",
                            "channel_top": float(resist_price),
                            "channel_bottom": float(support_price) if missed and support_price > 0 else None,
                            "stages": len(prices_l),
                            "stop_loss": float(hard_sl_l), "target_price": float(rr3_l),
                        }
                        for i, (p, a) in enumerate(zip(prices_l, alloc_l)):
                            payload[f"entry{i+1}_price"] = float(p)
                            payload[f"entry{i+1}_weight"] = int(a / p) if p > 0 else 0
                        quick_add_journal(payload)
                except Exception as e:
                    st.caption(f"시뮬레이션 오류: {e}")
            else:
                st.caption("저항선을 입력하면 시뮬레이션이 표시됩니다.")

            return {
                "show_lines": show_lines, "missed": missed,
                "resist_price": resist_price, "support_price": support_price,
                "hard_sl_pct": st_sl_pct, "budget": budget_l,
                "avg_price": avg_price_l, "hard_sl": hard_sl_l,
                "target_price": rr3_l,
                "prices": prices_l, "alloc": alloc_l, "loss": loss_l,
            }

        # ── 4개 탭 ────────────────────────────────────────────────
        tab_break, tab_reversal, tab_bluechip, tab_sideways = st.tabs([
            "🏺 손잡이컵", "📉 역추세", "🏦 우량주", "🔄 횡보돌파"
        ])

        with tab_break:
            break_r = _breakout_tab("break", "show_break_lines", default_sl_pct=4.0, missed_sl_pct=5.0)

        with tab_reversal:
            rev_r = _breakout_tab("rev", "show_rev_lines", default_sl_pct=7.0, missed_sl_pct=8.0, missed_logic="zone")

        with tab_bluechip:
            bc_r = _breakout_tab("bc", "show_bc_lines", missed_sl_pct=10.0, missed_logic="zone", force_zone=True, rr_multiple=3)

        with tab_sideways:
            sw_r = _breakout_tab("sw", "show_sw_lines", default_sl_pct=7.0, missed_sl_pct=7.0, missed_logic="zone", rr_multiple=5)

        # ── 활성 탭 결정 ──────────────────────────────────────────
        if break_r["show_lines"]:
            active_brk = break_r
        elif rev_r["show_lines"]:
            active_brk = rev_r
        elif bc_r["show_lines"]:
            active_brk = bc_r
        elif sw_r["show_lines"]:
            active_brk = sw_r
        else:
            active_brk = break_r

        return {
            "mid_term": {"show_lines": False},
            "short_term": {
                "show_lines": active_brk["show_lines"],
                "resist_price": active_brk["resist_price"],
                "support_price": active_brk.get("support_price", 0.0),
                "missed": active_brk.get("missed", False),
                "hard_sl_pct": active_brk["hard_sl_pct"],
                "target_price": active_brk.get("target_price", 0.0),
                "budget": active_brk["budget"],
            },
            "calc_res":     None,
            "rr_targets":   None,
            "st_avg_price": active_brk["avg_price"],
            "st_hard_sl":   active_brk["hard_sl"],
            "st_prices":    active_brk["prices"],
            "st_alloc":     active_brk["alloc"],
            "st_loss":      active_brk["loss"],
        }
