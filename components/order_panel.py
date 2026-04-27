import streamlit as st
from datetime import datetime
import pandas as pd
from data_loader import StockDataLoader

def render_order_panel(symbol, name, c_price):
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🤖 자동 주문 조건 설정 (가상 감시)", expanded=True):
        order_cols = st.columns(2)
        
        # 🟢 [좌측] 매수 조건
        with order_cols[0]:
            st.markdown("<h5 style='color: #2ecc71; margin-bottom: 15px;'>🟢 매수 (Buy) 설정</h5>", unsafe_allow_html=True)
            
            buy_strat = st.radio("🟢 매수 전략 선택", ["미사용", "일반 지정가 매수", "트레일링 매수", "조건부 분할매수"], horizontal=True, key="buy_strat")
            st.divider()
            
            if buy_strat == "일반 지정가 매수":
                c1, c2 = st.columns([5, 5])
                with c1:
                    b_p1 = st.number_input("지정가격(원)", value=int(c_price), step=50, key="b_p1")
                with c2:
                    b_q1 = st.number_input("수량(주)", value=1, step=1, key="b_q1")
                st.markdown(f"ℹ️ **지정가:** `{b_p1:,}`원에 `{b_q1:,}`주 매수 주문을 감시합니다.")
                
            elif buy_strat == "트레일링 매수":
                c1, c2, c3 = st.columns([4, 3, 3])
                with c1:
                    b_base2 = st.number_input("기준가격(원)", value=int(c_price), step=50, key="b_base2")
                with c2:
                    b_drop2 = st.number_input("하락폭(%)", value=0.5, step=0.1, key="b_drop2")
                with c3:
                    b_reb2 = st.number_input("반등폭(%)", value=0.1, step=0.05, key="b_reb2")
                    
                c4, _ = st.columns([4, 6])
                with c4:
                    b_q2 = st.number_input("매수수량(주)", value=1, step=1, key="b_q2")
                    
                st.markdown(f"ℹ️ **조건:** `{b_base2:,}`원 도달 시, 최저점 대비 `{b_drop2}%` 하락한 뒤 `{b_reb2}%` 반등하면 `{b_q2:,}`주 매수")
                
            elif buy_strat == "조건부 분할매수":
                st.markdown("ℹ️ 상단 분석 전략(중기/단기) 기반으로 1~4차 조건 도달 시 자동 분할 매수를 대기합니다.")
                
            st.markdown("<br>", unsafe_allow_html=True)
            if buy_strat != "미사용":
                if st.button("🟢 매수 조건 감시 시작", use_container_width=True, key="btn_buy_start"):
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
                    elif buy_strat == "조건부 분할매수":
                        new_order["desc"] = "전략별 1~4차 분할 매집"
                        new_order["qty"] = "전략 비중 기준"
                        
                    st.session_state.watch_orders.append(new_order)
                    st.success(f"[{name}] {buy_strat} 감시가 등록되었습니다.")

        # 🔴 [우측] 매도 조건
        with order_cols[1]:
            st.markdown("<h5 style='color: #ef5350; margin-bottom: 15px;'>🔴 매도 (Sell) 설정</h5>", unsafe_allow_html=True)
            
            sell_strat = st.radio("🔴 매도 전략 선택", ["미사용", "목표가 익절", "손절매", "트레일링 스탑"], horizontal=True, key="sell_strat")
            st.divider()
            
            if sell_strat == "목표가 익절":
                c1, c2 = st.columns([5, 5])
                with c1:
                    s_p1 = st.number_input("목표가격(원)", value=int(c_price * 1.05), step=50, key="s_p1")
                with c2:
                    s_q1 = st.number_input("매도수량(주)", value=1, step=1, key="s_q1")
                st.markdown(f"ℹ️ **조건:** 주가가 `{s_p1:,}`원 도달 시 `{s_q1:,}`주 전량 매도")
                
            elif sell_strat == "손절매":
                c1, c2 = st.columns([5, 5])
                with c1:
                    s_p2 = st.number_input("손절가격(원)", value=int(c_price * 0.95), step=50, key="s_p2")
                with c2:
                    s_q2 = st.number_input("매도수량(주)", value=1, step=1, key="s_q2")
                st.markdown(f"ℹ️ **조건:** 주가가 `{s_p2:,}`원 이하로 추락 시 `{s_q2:,}`주 전량 손절")
                
            elif sell_strat == "트레일링 스탑":
                c1, c2, c3 = st.columns([4, 3, 3])
                with c1:
                    s_base3 = st.number_input("익절기준가(원)", value=int(c_price * 1.03), step=50, key="s_base3")
                with c2:
                    s_drop3 = st.number_input("하락폭(%)", value=1.0, step=0.1, key="s_drop3")
                with c3:
                    s_q3 = st.number_input("매도수량(주)", value=1, step=1, key="s_q3")
                st.markdown(f"ℹ️ **조건:** `{s_base3:,}`원 도달 이후 형성된 최고점 대비 `{s_drop3}%` 하락 시 `{s_q3:,}`주 전량 매도")
                
            st.markdown("<br>", unsafe_allow_html=True)
            if sell_strat != "미사용":
                if st.button("🔴 매도 조건 감시 시작", use_container_width=True, key="btn_sell_start"):
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
                    st.success(f"[{name}] {sell_strat} 감시가 등록되었습니다.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #f39c12; margin-bottom: 15px;'>📋 실시간 감시 주문 현황</h4>", unsafe_allow_html=True)
    
    if not st.session_state.watch_orders:
        st.info("현재 등록된 감시 주문이 없습니다. 상단 패널에서 전략을 설정하고 [감시 시작]을 눌러보세요.")
    else:
        grouped_orders = {}
        for order in st.session_state.watch_orders:
            k = f"{order['name']} ({order['code']})"
            if k not in grouped_orders:
                grouped_orders[k] = []
            grouped_orders[k].append(order)
            
        for stock_key, orders in grouped_orders.items():
            with st.expander(f"📦 {stock_key} - 감시 주문 {len(orders)}건", expanded=True):
                df_data = []
                for ord_item in orders:
                    status_text = ord_item['status']
                    if "target_price" in ord_item and ord_item['target_price'] > 0:
                        item_c_price = StockDataLoader.get_current_price(ord_item['code'])
                        if not item_c_price:
                            item_c_price = c_price
                            
                        t_p = ord_item['target_price']
                        diff_pct = ((item_c_price / t_p) - 1) * 100
                        
                        if ord_item['type'] == "🟢 매수":
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
                        "구분": ord_item['type'],
                        "전략": ord_item['strat'],
                        "수량": ord_item['qty'],
                        "상세 조건": ord_item['desc'],
                        "상태": status_text
                    })
                st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #3498db; margin-bottom: 15px;'>🛒 증권사 접수 완료 내역 (미체결)</h4>", unsafe_allow_html=True)
    
    if not st.session_state.registered_orders:
        st.info("증권사 서버에 접수된 미체결 주문이 없습니다.")
    else:
        grouped_registered = {}
        for order in st.session_state.registered_orders:
            k = f"{order['name']} ({order['code']})"
            if k not in grouped_registered:
                grouped_registered[k] = []
            grouped_registered[k].append(order)
            
        for stock_key, orders in grouped_registered.items():
            with st.expander(f"📥 {stock_key} - 접수 대기 {len(orders)}건", expanded=True):
                df_data = []
                for ord_item in orders:
                    df_data.append({
                        "접수시간": ord_item['time'],
                        "구분": ord_item['type'],
                        "전략": ord_item['strat'],
                        "수량": ord_item['qty'],
                        "주문조건": ord_item['desc'],
                        "상태": ord_item['status']
                    })
                st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)
