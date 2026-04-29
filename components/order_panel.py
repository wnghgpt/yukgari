import streamlit as st
from datetime import datetime
import pandas as pd
from data_loader import StockDataLoader
from kis_client import KISClient


def render_order_input(symbol, name, c_price, mid_term=None):
    with st.container(border=True):
        st.markdown("<div style='font-size: 0.95rem; font-weight: bold; color: #F39C12; margin-bottom: 10px;'>🛒 트레이딩 주문창</div>", unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["일반 주문", "🟢 자동 매수", "🔴 자동 매도"])
        
        with tab1:
            st.markdown("<h6 style='color: #3498db; margin-bottom: 10px;'>🛒 일반 주문 (즉시 전송)</h6>", unsafe_allow_html=True)
            
            c_side, c_type = st.columns(2)
            with c_side:
                ord_side = st.radio("매매 구분", ["매수", "매도"], horizontal=True, key="normal_ord_side")
            with c_type:
                ord_type = st.radio("주문 구분", ["지정가", "시장가"], horizontal=True, key="normal_ord_type")
            
            if ord_type == "지정가":
                n_price = st.number_input("주문 가격(원)", value=int(c_price), step=50, key="n_price")
            else:
                n_price = int(c_price)
                st.markdown(f"<p style='font-size: 0.8rem; color: #d1d4dc;'>ℹ️ <b>시장가</b> (현재가 약 {c_price:,}원 기준)</p>", unsafe_allow_html=True)
                
            n_qty = st.number_input("주문 수량(주)", value=1, step=1, key="n_qty")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🛒 주문 전송", use_container_width=True, key="btn_normal_order"):
                acc_idx = st.session_state.get("selected_acc_idx", 4)
                kis = KISClient(acc_idx=acc_idx)
                
                is_buy_flag = (ord_side == "매수")
                res = kis.post_order_cash(
                    code=symbol,
                    qty=int(n_qty),
                    price=int(n_price),
                    is_buy=is_buy_flag,
                    is_market=(ord_type == "시장가")
                )
                
                if res and res.get("rt_cd") == "0":
                    side_prefix = "🟢 매수" if is_buy_flag else "🔴 매도"
                    new_reg = {
                        "code": symbol,
                        "name": name,
                        "type": f"{side_prefix} ({ord_type})",
                        "strat": "일반 주문",
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "qty": f"{n_qty:,}주",
                        "desc": f"{n_price:,}원" if ord_type == "지정가" else "시장가",
                        "status": "체결 대기" if ord_type == "지정가" else "체결 완료"
                    }
                    st.session_state.registered_orders.append(new_reg)
                    st.success(f"[{name}] {side_prefix} {n_qty}주 주문 성공! (주문번호: {res.get('output', {}).get('ODNO', 'N/A')})")
                else:
                    err_msg = res.get("msg1", "알 수 없는 오류") if res else "응답 없음"
                    st.error(f"❌ 주문 실패: {err_msg}")
                
        with tab2:
            st.markdown("<h6 style='color: #2ecc71; margin-bottom: 10px;'>🟢 자동 매수 조건 감시</h6>", unsafe_allow_html=True)
            buy_strat = st.radio("🟢 매수 전략", ["미사용", "일반 지정가 매수", "트레일링 매수", "조건부 분할매수"], key="buy_strat_tab")
            st.divider()
            
            if buy_strat == "일반 지정가 매수":
                b_p1 = st.number_input("지정가격(원)", value=int(c_price), step=50, key="b_p1")
                b_q1 = st.number_input("수량(주)", value=1, step=1, key="b_q1")
                st.markdown(f"<p style='font-size: 0.8rem; color: #d1d4dc;'>ℹ️ {b_p1:,}원에 {b_q1:,}주 매수 감시</p>", unsafe_allow_html=True)
                
            elif buy_strat == "트레일링 매수":
                b_base2 = st.number_input("기준가격(원)", value=int(c_price), step=50, key="b_base2")
                b_drop2 = st.number_input("하락폭(%)", value=0.5, step=0.1, key="b_drop2")
                b_reb2 = st.number_input("반등폭(%)", value=0.1, step=0.05, key="b_reb2")
                b_q2 = st.number_input("매수수량(주)", value=1, step=1, key="b_q2")
                st.markdown(f"<p style='font-size: 0.8rem; color: #d1d4dc;'>ℹ️ {b_base2:,}원 도달 후 {b_drop2}%↓ & {b_reb2}%↑ 시 {b_q2:,}주 매수</p>", unsafe_allow_html=True)
                
            elif buy_strat == "조건부 분할매수":
                st.markdown("<p style='font-size: 0.8rem; color: #d1d4dc;'>ℹ️ 중기 전략 타점(1~4차)에 도달 후 1.0% 반등 시 매수하는 4개의 주문을 일괄 등록합니다.</p>", unsafe_allow_html=True)
                
                if mid_term:
                    from calculator import StrategyCalculator
                    try:
                        calc_res = StrategyCalculator.calculate_pyramid(
                            channel_top=float(mid_term["channel_top"]),
                            channel_bot=float(mid_term["channel_bot"]),
                            hard_stop_loss=float(mid_term["hard_sl"]),
                            base_budget=float(mid_term["budget"]),
                            weights=mid_term["weights"]
                        )
                        zones = calc_res.get("zones", [])
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("⚡ 중기 전략 일괄 감시 시작", use_container_width=True, key="btn_batch_mid_term"):
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
                            st.success(f"[{name}] 중기 전략 1~4차 트레일링 매수 감시가 일괄 등록되었습니다.")
                    except Exception as e:
                        st.error(f"전략 계산 오류: {e}")
                else:
                    st.warning("상단에서 중기 전략 설정을 먼저 완료해 주세요.")
                
            st.markdown("<br>", unsafe_allow_html=True)
            if buy_strat not in ["미사용", "조건부 분할매수"]:
                if st.button("🟢 매수 감시 시작", use_container_width=True, key="btn_buy_start_tab"):
                    new_order = {
                        "code": symbol,
                        "name": name,
                        "type": "🟢 매수",
                        "strat": buy_strat,
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "status": "🟡 감시 중",
                        "target_price": 0
                    }
                    if buy_strat == "일반 지정가 매수":
                        new_order["desc"] = f"지정가 {b_p1:,}원"
                        new_order["qty"] = f"{b_q1:,}주"
                        new_order["target_price"] = b_p1
                    elif buy_strat == "트레일링 매수":
                        new_order["desc"] = f"{b_base2:,}원 도달 후 {b_drop2}%↓ & {b_reb2}%↑"
                        new_order["qty"] = f"{b_q2:,}주"
                        new_order["target_price"] = b_base2
                        
                    st.session_state.watch_orders.append(new_order)
                    st.success(f"[{name}] {buy_strat} 감시 등록.")
                    
        with tab3:
            st.markdown("<h6 style='color: #ef5350; margin-bottom: 10px;'>🔴 자동 매도 조건 감시</h6>", unsafe_allow_html=True)
            sell_strat = st.radio("🔴 매도 전략", ["미사용", "목표가 익절", "손절매", "트레일링 스탑"], key="sell_strat_tab")
            st.divider()
            
            if sell_strat == "목표가 익절":
                s_p1 = st.number_input("목표가격(원)", value=int(c_price * 1.05), step=50, key="s_p1")
                s_q1 = st.number_input("매도수량(주)", value=1, step=1, key="s_q1")
                st.markdown(f"<p style='font-size: 0.8rem; color: #d1d4dc;'>ℹ️ {s_p1:,}원 도달 시 {s_q1:,}주 매도</p>", unsafe_allow_html=True)
                
            elif sell_strat == "손절매":
                s_p2 = st.number_input("손절가격(원)", value=int(c_price * 0.95), step=50, key="s_p2")
                s_q2 = st.number_input("매도수량(주)", value=1, step=1, key="s_q2")
                st.markdown(f"<p style='font-size: 0.8rem; color: #d1d4dc;'>ℹ️ {s_p2:,}원 이하 추락 시 {s_q2:,}주 손절</p>", unsafe_allow_html=True)
                
            elif sell_strat == "트레일링 스탑":
                s_base3 = st.number_input("익절기준가(원)", value=int(c_price * 1.03), step=50, key="s_base3")
                s_drop3 = st.number_input("하락폭(%)", value=1.0, step=0.1, key="s_drop3")
                s_q3 = st.number_input("매도수량(주)", value=1, step=1, key="s_q3")
                st.markdown(f"<p style='font-size: 0.8rem; color: #d1d4dc;'>ℹ️ {s_base3:,}원 도달 후 최고점 대비 {s_drop3}%↓ 시 {s_q3:,}주 매도</p>", unsafe_allow_html=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            if sell_strat != "미사용":
                if st.button("🔴 매도 감시 시작", use_container_width=True, key="btn_sell_start_tab"):
                    new_order = {
                        "code": symbol,
                        "name": name,
                        "type": "🔴 매도",
                        "strat": sell_strat,
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "status": "🟡 감시 중",
                        "target_price": 0
                    }
                    if sell_strat == "목표가 익절":
                        new_order["desc"] = f"익절가 {s_p1:,}원"
                        new_order["qty"] = f"{s_q1:,}주"
                        new_order["target_price"] = s_p1
                    elif sell_strat == "손절매":
                        new_order["desc"] = f"손절가 {s_p2:,}원"
                        new_order["qty"] = f"{s_q2:,}주"
                        new_order["target_price"] = s_p2
                    elif sell_strat == "트레일링 스탑":
                        new_order["desc"] = f"{s_base3:,}원 달성 후 최고점 대비 {s_drop3}%↓"
                        new_order["qty"] = f"{s_q3:,}주"
                        new_order["target_price"] = s_base3
                        
                    st.session_state.watch_orders.append(new_order)
                    st.success(f"[{name}] {sell_strat} 감시 등록.")


def render_order_status(symbol, name, c_price):
    st.markdown("<h4 style='color: #f39c12; margin-bottom: 15px;'>📋 실시간 감시 주문 현황</h4>", unsafe_allow_html=True)
    
    if not st.session_state.watch_orders:
        st.info("현재 등록된 감시 주문이 없습니다. 트레이딩 주문창에서 감시를 시작해보세요.")
    else:
        df_data = []
        for ord_item in st.session_state.watch_orders:
            status_text = ord_item['status']
            if "target_price" in ord_item and ord_item['target_price'] > 0:
                item_c_price = StockDataLoader.get_current_price(ord_item['code'])
                if not item_c_price:
                    item_c_price = c_price
                    
                t_p = ord_item['target_price']
                diff_pct = ((item_c_price / t_p) - 1) * 100
                
                if "매수" in ord_item['type']:
                    if diff_pct <= 0:
                        status_text = "🟢 타점 도달!"
                    else:
                        status_text = f"🟡 감시 중 ({diff_pct:+.1f}%)"
                else:
                    if diff_pct >= 0:
                        status_text = "🟢 타점 도달!"
                    else:
                        status_text = f"🟡 감시 중 ({diff_pct:+.1f}%)"
                        
            df_data.append({
                "시간": ord_item['time'],
                "종목": f"{ord_item['name']}({ord_item['code']})",
                "구분": ord_item['type'],
                "전략": ord_item['strat'],
                "수량": ord_item['qty'],
                "상세 조건": ord_item['desc'],
                "상태": status_text
            })
        st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #3498db; margin-bottom: 15px;'>🛒 증권사 접수 완료 내역 (미체결/체결)</h4>", unsafe_allow_html=True)
    
    if not st.session_state.registered_orders:
        st.info("증권사 서버에 접수된 주문 내역이 없습니다.")
    else:
        df_reg_data = []
        for ord_item in st.session_state.registered_orders:
            df_reg_data.append({
                "접수시간": ord_item['time'],
                "종목": f"{ord_item['name']}({ord_item['code']})",
                "구분": ord_item['type'],
                "전략": ord_item['strat'],
                "수량": ord_item['qty'],
                "주문조건": ord_item['desc'],
                "상태": ord_item['status']
            })
        st.dataframe(pd.DataFrame(df_reg_data), use_container_width=True, hide_index=True)

