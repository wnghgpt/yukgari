import streamlit as st
from calculator import StrategyCalculator

def render_scenario_cards(mid_term_params, short_term_params, c_price, st_avg_price, st_hard_sl, st_sum_w, st_prices, st_weights, st_alloc, st_budget, st_loss, symbol=None, name=None):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h4 style='margin-bottom: 15px;'>📍 분할 매수 시나리오별 비교</h4>", unsafe_allow_html=True)
    
    unit = st.session_state.get("unit", "원")
    is_overseas = st.session_state.get("is_overseas", False)
    
    # 가격 포맷팅 헬퍼
    def fmt_p(val):
        if is_overseas:
            return f"{val:,.2f}"
        return f"{int(val):,}"

    sc_cols = st.columns(3)
    
    # 1번 카드 (단기 - 돌파 매매)
    with sc_cols[1]:
        try:
            sc_res = StrategyCalculator.calculate_pyramid(
                channel_top=float(mid_term_params["channel_top"]),
                channel_bot=float(mid_term_params["channel_bot"]),
                hard_stop_loss=float(mid_term_params["hard_sl"]),
                base_budget=float(mid_term_params["budget"]),
            )
            with st.container(border=True):
                mid_loss_amt = sc_res['total_risk_amount']
                mid_loss_str = f"{mid_loss_amt:.1f}" if is_overseas else f"{mid_loss_amt/10000:.0f}만"
                steps = sc_res.get("steps", 4)
                w_str = "20/30/50" if steps == 3 else "15/25/35/25"
                st.markdown(f"<h5 style='color: #3498DB; margin-bottom: 2px;'>📊 풀백/눌림목 매매</h5><div style='font-size: 0.6rem; color: #8a8d9a; margin-bottom: 8px;'>전략: 채널 내 {steps}단계 균등분할 ({w_str})</div>", unsafe_allow_html=True)
                st.markdown(f"""
                    <div style='font-size: 0.8rem; line-height: 1.4;'>
                        <b>평단:</b> {fmt_p(sc_res['avg_price'])}{unit} | <b>보유:</b> {int(sc_res['total_qty']):,}주<br>
                        <b style='color: #ef5350;'>손실: {sc_res['loss_pct']:.2f}% <span style='font-weight: normal; font-size: 0.75rem;'>(-{mid_loss_str})</span></b>
                    </div>
                    <hr style='margin: 8px 0;'>
                """, unsafe_allow_html=True)
                for i, zone in enumerate(sc_res['zones']):
                    lbl = f"{i+1}차"
                    qty = int(zone['qty'])
                    amt_val = zone['allocate_amt'] / 10000 if not is_overseas else zone['allocate_amt']
                    amt_unit = "만" if not is_overseas else ""
                    drop_pct = ((zone['price'] / c_price) - 1) * 100
                    color_pct = "#2ecc71" if drop_pct >= 0 else "#ef5350"
                    st.markdown(f"""
                        <div style='font-size: 0.65rem; white-space: nowrap; margin-bottom: 3px; display: flex; justify-content: space-between;'>
                            <span><b>{lbl}:</b> {fmt_p(zone['price'])}{unit} <span style='color: {color_pct}; font-size: 0.6rem;'>({drop_pct:+.1f}%)</span></span>
                            <span style='color: #8a8d9a;'>{qty}주 ({amt_val:.1f}{amt_unit})</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                mid_hsl_pct = mid_term_params.get("hard_sl_pct", 4.0)
                mid_rr3 = sc_res['avg_price'] + 3 * (sc_res['avg_price'] - sc_res['hard_stop_loss'])
                st.markdown(f"""
                    <div style='font-size: 0.78rem; color: #ef5350; display: flex; justify-content: space-between;'>
                        <b>최종손절 <span style='font-weight: normal; font-size: 0.65rem;'>(-{mid_hsl_pct:.1f}%)</span>:</b>
                        <b>{fmt_p(sc_res['hard_stop_loss'])}{unit}</b>
                    </div>
                    <div style='font-size: 0.78rem; color: #2ecc71; display: flex; justify-content: space-between; margin-top: 3px;'>
                        <b>목표가 <span style='font-weight: normal; font-size: 0.65rem;'>(RR 3x)</span>:</b>
                        <b>{fmt_p(mid_rr3)}{unit}</b>
                    </div>

                <br>
                <div style='text-align: center;'>
                    <p style='font-size: 0.75rem; color: #d1d4dc; margin-bottom: 5px;'>💡 타점 이하 도달 후 1.0%↑ 반등 시 매수</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("⚡ 중기 전략 일괄 감시 시작", width="stretch", key="btn_batch_mid_card"):
                    from datetime import datetime
                    if symbol and name:
                        zones = sc_res.get("zones", [])
                        for i, zone in enumerate(zones):
                            target_p = float(zone["price"]) if is_overseas else int(zone["price"])
                            qty = int(zone["qty"])
                            if qty <= 0:
                                qty = 1
                                
                            new_order = {
                                "code": symbol,
                                "name": name,
                                "type": f"🟢 매수 ({i+1}차)",
                                "strat": "중기 분할매수 (트레일링)",
                                "time": datetime.now().strftime("%H:%M:%S"),
                                "status": "🟡 감시 중",
                                "target_price": target_p,
                                "desc": f"{fmt_p(target_p)}{unit} 이하 도달 후 1.0%↑ 반등 시 매수",
                                "qty": f"{qty:,}주"
                            }
                            
                            from supabase_db import SupabaseDB
                            db_res = SupabaseDB.insert_watch_order(
                                stock_code=symbol,
                                stock_name=name,
                                order_type=f"🟢 매수 ({i+1}차)",
                                strat_name="중기 분할매수 (트레일링)",
                                target_price=target_p,
                                qty=f"{qty:,}주"
                            )
                            if db_res:
                                new_order["id"] = db_res.get("id")
                                
                            st.session_state.watch_orders.append(new_order)
                        st.success(f"[{name}] 1~4차 일괄 등록 완료!")
                    else:
                        st.warning("종목 정보가 누락되었습니다.")
        except Exception as e:
            st.error(f"계산 오류 발생: {e}")
            
    # 2번 카드 (중기 - 풀백/눌림목 매매)
    with sc_cols[0]:
        if st_avg_price > 0 and st_sum_w > 0:
            try:
                st_total_qty = int(st_budget / st_avg_price) if st_avg_price > 0 else 0
                st_loss_pct = (st_loss / st_budget) * 100 if st_budget > 0 else 0
                
                with st.container(border=True):
                    e1_pct = short_term_params.get("entry1_pct", 2.0)
                    e2_pct = short_term_params.get("entry2_pct", 1.0)
                    sl_pct = short_term_params.get("hard_sl_pct", 4.0)
                    resist_p = short_term_params.get("resist_price", 0)
                    support_p = short_term_params.get("support_price", 0)
                    st.markdown(f"<h5 style='color: #E74C3C; margin-bottom: 2px;'>⚡ 돌파 매매</h5><div style='font-size: 0.6rem; color: #8a8d9a; margin-bottom: 8px;'>저항선+{e1_pct:.1f}% / 지지선+{e2_pct:.1f}% | 70:30 | 손절 -{sl_pct:.1f}%</div>", unsafe_allow_html=True)
                    st_loss_val = st_loss / 10000 if not is_overseas else st_loss
                    loss_str = f"{st_loss_val:.1f}{'만' if not is_overseas else ''}"
                    st.markdown(f"""
                        <div style='font-size: 0.8rem; line-height: 1.4;'>
                            <b>평단:</b> {fmt_p(st_avg_price)}{unit} | <b>보유:</b> {st_total_qty:,}주<br>
                            <b style='color: #ef5350;'>손실: {st_loss_pct:.2f}% <span style='font-weight: normal; font-size: 0.75rem;'>(-{loss_str})</span></b>
                        </div>
                        <hr style='margin: 8px 0;'>
                    """, unsafe_allow_html=True)

                    ref_labels = [f"저항선+{e1_pct:.1f}%", f"지지선+{e2_pct:.1f}%"]
                    for i, (p, w) in enumerate(zip(st_prices, st_weights)):
                        amt = st_alloc[i]
                        qty = int(amt / p) if p > 0 else 0
                        amt_val = amt / 10000 if not is_overseas else amt
                        amt_unit = "만" if not is_overseas else ""
                        drop_pct = ((p / c_price) - 1) * 100
                        color_pct = "#2ecc71" if drop_pct >= 0 else "#ef5350"
                        st.markdown(f"""
                            <div style='font-size: 0.65rem; white-space: nowrap; margin-bottom: 3px; display: flex; justify-content: space-between;'>
                                <span><b>{i+1}차:</b> {fmt_p(p)}{unit} <span style='color: {color_pct}; font-size: 0.6rem;'>({drop_pct:+.1f}%)</span> <span style='color:#555; font-size:0.55rem;'>{ref_labels[i]}</span></span>
                                <span style='color: #8a8d9a;'>{qty}주 ({amt_val:.1f}{amt_unit})</span>
                            </div>
                        """, unsafe_allow_html=True)

                    st_rr3 = st_avg_price + 3 * (st_avg_price - st_hard_sl)
                    st.markdown(f"""
                        <div style='font-size: 0.78rem; color: #ef5350; display: flex; justify-content: space-between; margin-top: 4px;'>
                            <b>최종손절 <span style='font-weight: normal; font-size: 0.65rem;'>(지지선-{sl_pct:.1f}%)</span>:</b>
                            <b>{fmt_p(st_hard_sl)}{unit}</b>
                        </div>
                        <div style='font-size: 0.78rem; color: #2ecc71; display: flex; justify-content: space-between; margin-top: 3px;'>
                            <b>목표가 <span style='font-weight: normal; font-size: 0.65rem;'>(RR 3x)</span>:</b>
                            <b>{fmt_p(st_rr3)}{unit}</b>
                        </div>
                    """, unsafe_allow_html=True)
            except:
                st.error("계산 오류")
        else:
            with st.container(border=True):
                st.markdown(f"<h5 style='color: #E74C3C; margin-bottom: 10px;'>⚡ 돌파 매매</h5>", unsafe_allow_html=True)
                st.markdown("<div style='font-size: 0.8rem; color:#8a8d9a;'>저항선 미설정</div>", unsafe_allow_html=True)
                
    # 3번 카드
    with sc_cols[2]:
        with st.container(border=True):
            st.markdown(f"<h5 style='color: #7f8c8d; margin-bottom: 10px;'>🛡️ 장기 </h5>", unsafe_allow_html=True)
            st.markdown("<div style='height: 100px; display: flex; align-items: center; justify-content: center; color: #7f8c8d;'>-</div>", unsafe_allow_html=True)
