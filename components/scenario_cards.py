import streamlit as st
from calculator import StrategyCalculator

def render_scenario_cards(mid_term_params, short_term_params, c_price, st_avg_price, st_hard_sl, st_sum_w, st_prices, st_weights, st_alloc, st_budget, st_loss, symbol=None, name=None):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h4 style='margin-bottom: 15px;'>📍 분할 매수 시나리오별 비교</h4>", unsafe_allow_html=True)
    
    sc_cols = st.columns(3)
    
    # 1번 카드 (중기)
    with sc_cols[0]:
        try:
            sc_res = StrategyCalculator.calculate_pyramid(
                channel_top=float(mid_term_params["channel_top"]),
                channel_bot=float(mid_term_params["channel_bot"]),
                hard_stop_loss=float(mid_term_params["hard_sl"]),
                base_budget=float(mid_term_params["budget"]),
                weights=mid_term_params["weights"]
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
                
                <br>
                <div style='text-align: center;'>
                    <p style='font-size: 0.75rem; color: #d1d4dc; margin-bottom: 5px;'>💡 타점 이하 도달 후 1.0%↑ 반등 시 매수</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("⚡ 중기 전략 일괄 감시 시작", use_container_width=True, key="btn_batch_mid_card"):
                    from datetime import datetime
                    if symbol and name:
                        zones = sc_res.get("zones", [])
                        for i, zone in enumerate(zones):
                            target_p = int(zone["price"])
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
                                "desc": f"{target_p:,}원 이하 도달 후 1.0%↑ 반등 시 매수",
                                "qty": f"{qty:,}주"
                            }
                            st.session_state.watch_orders.append(new_order)
                        st.success(f"[{name}] 1~4차 일괄 등록 완료!")
                    else:
                        st.warning("종목 정보가 누락되었습니다.")
        except:
            st.error("계산 오류")
            
    # 2번 카드 (단기)
    with sc_cols[1]:
        if st_avg_price > 0 and st_sum_w > 0:
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
