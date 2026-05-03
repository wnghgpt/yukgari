import streamlit as st
from datetime import datetime
import pandas as pd
from data_loader import StockDataLoader
from kis_client import KISClient


def render_order_input(symbol, name, c_price, mid_term=None):
    unit = st.session_state.get("unit", "원")
    is_overseas = st.session_state.get("is_overseas", False)
    
    # 입력용 step 및 format 설정
    p_step = 0.01 if is_overseas else 50
    p_fmt = "%.2f" if is_overseas else "%d"
    
    # 가격 포맷팅 헬퍼
    def fmt_p(val):
        if is_overseas:
            return f"{val:,.2f}"
        return f"{int(val):,}"

    with st.container(border=True):
        st.markdown("<div style='font-size: 0.95rem; font-weight: bold; color: #F39C12; margin-bottom: 10px;'>🛒 트레이딩 주문창</div>", unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["일반 주문", "🟢 자동 매수", "🔴 자동 매도"])
        
        with tab1:
            st.markdown(f"<h6 style='color: #3498db; margin-bottom: 10px;'>🛒 일반 주문 (즉시 전송)</h6>", unsafe_allow_html=True)
            
            c_side, c_type = st.columns(2)
            with c_side:
                ord_side = st.radio("매매 구분", ["매수", "매도"], horizontal=True, key="normal_ord_side")
            with c_type:
                ord_type = st.radio("주문 구분", ["지정가", "시장가"], horizontal=True, key="normal_ord_type")
            
            if ord_type == "지정가":
                n_price = st.number_input(f"주문 가격({unit})", value=float(c_price) if is_overseas else int(c_price), step=p_step, format=p_fmt, key="n_price")
            else:
                n_price = c_price
                st.markdown(f"<p style='font-size: 0.8rem; color: #d1d4dc;'>ℹ️ <b>시장가</b> (현재가 약 {fmt_p(c_price)}{unit} 기준)</p>", unsafe_allow_html=True)
                
            n_qty = st.number_input("주문 수량(주)", value=1, step=1, key="n_qty")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🛒 주문 전송", use_container_width=True, key="btn_normal_order"):
                acc_idx = st.session_state.get("selected_acc_idx", 4)
                kis = KISClient(acc_idx=acc_idx)
                
                is_buy_flag = (ord_side == "매수")
                # 국내/해외 가격 타입 처리
                send_price = float(n_price) if is_overseas else int(n_price)
                
                res = kis.post_order_cash(
                    code=symbol,
                    qty=int(n_qty),
                    price=send_price,
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
                        "desc": f"{fmt_p(n_price)}{unit}" if ord_type == "지정가" else "시장가",
                        "status": "체결 대기" if ord_type == "지정가" else "체결 완료"
                    }
                    st.session_state.registered_orders.append(new_reg)
                    st.success(f"[{name}] {side_prefix} {n_qty}주 주문 성공! (주문번호: {res.get('output', {}).get('ODNO', 'N/A')})")
                else:
                    err_msg = res.get("msg1", "알 수 없는 오류") if res else "응답 없음"
                    st.error(f"❌ 주문 실패: {err_msg}")
                
        with tab2:
            st.markdown(f"<h6 style='color: #2ecc71; margin-bottom: 10px;'>🟢 자동 매수 조건 감시</h6>", unsafe_allow_html=True)
            buy_strat = st.radio("🟢 매수 전략", ["미사용", "일반 지정가 매수", "트레일링 매수", "조건부 분할매수"], key="buy_strat_tab")
            st.divider()
            
            if buy_strat == "일반 지정가 매수":
                b_p1 = st.number_input(f"지정가격({unit})", value=float(c_price) if is_overseas else int(c_price), step=p_step, format=p_fmt, key="b_p1")
                b_q1 = st.number_input("수량(주)", value=1, step=1, key="b_q1")
                st.markdown(f"<p style='font-size: 0.8rem; color: #d1d4dc;'>ℹ️ {fmt_p(b_p1)}{unit}에 {b_q1:,}주 매수 감시</p>", unsafe_allow_html=True)
                
            elif buy_strat == "트레일링 매수":
                b_base2 = st.number_input(f"기준가격({unit})", value=float(c_price) if is_overseas else int(c_price), step=p_step, format=p_fmt, key="b_base2")
                b_drop2 = st.number_input("하락폭(%)", value=0.5, step=0.1, key="b_drop2")
                b_reb2 = st.number_input("반등폭(%)", value=0.1, step=0.05, key="b_reb2")
                b_q2 = st.number_input("매수수량(주)", value=1, step=1, key="b_q2")
                st.markdown(f"<p style='font-size: 0.8rem; color: #d1d4dc;'>ℹ️ {fmt_p(b_base2)}{unit} 도달 후 {b_drop2}%↓ & {b_reb2}%↑ 시 {b_q2:,}주 매수</p>", unsafe_allow_html=True)
                
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
                        new_order["desc"] = f"지정가 {fmt_p(b_p1)}{unit}"
                        new_order["qty"] = f"{b_q1:,}주"
                        new_order["target_price"] = b_p1
                    elif buy_strat == "트레일링 매수":
                        new_order["desc"] = f"{fmt_p(b_base2)}{unit} 도달 후 {b_drop2}%↓ & {b_reb2}%↑"
                        new_order["qty"] = f"{b_q2:,}주"
                        new_order["target_price"] = b_base2
                        
                    from supabase_db import SupabaseDB
                    db_res = SupabaseDB.insert_watch_order(
                        stock_code=symbol,
                        stock_name=name,
                        order_type=new_order["type"],
                        strat_name=buy_strat,
                        target_price=new_order["target_price"],
                        qty=new_order["qty"]
                    )
                    if db_res:
                        new_order["id"] = db_res.get("id")
                        
                    st.session_state.watch_orders.append(new_order)
                    st.success(f"[{name}] {buy_strat} 감시 등록.")
                    
        with tab3:
            st.markdown(f"<h6 style='color: #ef5350; margin-bottom: 10px;'>🔴 자동 매도 조건 감시</h6>", unsafe_allow_html=True)
            sell_strat = st.radio("🔴 매도 전략", ["미사용", "목표가 익절", "손절매", "트레일링 스탑"], key="sell_strat_tab")
            st.divider()
            
            if sell_strat == "목표가 익절":
                s_p1 = st.number_input(f"목표가격({unit})", value=float(c_price * 1.05) if is_overseas else int(c_price * 1.05), step=p_step, format=p_fmt, key="s_p1")
                s_q1 = st.number_input("매도수량(주)", value=1, step=1, key="s_q1")
                st.markdown(f"<p style='font-size: 0.8rem; color: #d1d4dc;'>ℹ️ {fmt_p(s_p1)}{unit} 도달 시 {s_q1:,}주 매도</p>", unsafe_allow_html=True)
                
            elif sell_strat == "손절매":
                s_p2 = st.number_input(f"손절가격({unit})", value=float(c_price * 0.95) if is_overseas else int(c_price * 0.95), step=p_step, format=p_fmt, key="s_p2")
                s_q2 = st.number_input("매도수량(주)", value=1, step=1, key="s_q2")
                st.markdown(f"<p style='font-size: 0.8rem; color: #d1d4dc;'>ℹ️ {fmt_p(s_p2)}{unit} 이하 추락 시 {s_q2:,}주 손절</p>", unsafe_allow_html=True)
                
            elif sell_strat == "트레일링 스탑":
                s_base3 = st.number_input(f"익절기준가({unit})", value=float(c_price * 1.03) if is_overseas else int(c_price * 1.03), step=p_step, format=p_fmt, key="s_base3")
                s_drop3 = st.number_input("하락폭(%)", value=1.0, step=0.1, key="s_drop3")
                s_q3 = st.number_input("매도수량(주)", value=1, step=1, key="s_q3")
                st.markdown(f"<p style='font-size: 0.8rem; color: #d1d4dc;'>ℹ️ {fmt_p(s_base3)}{unit} 도달 후 최고점 대비 {s_drop3}%↓ 시 {s_q3:,}주 매도</p>", unsafe_allow_html=True)
                
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
                        new_order["desc"] = f"익절가 {fmt_p(s_p1)}{unit}"
                        new_order["qty"] = f"{s_q1:,}주"
                        new_order["target_price"] = s_p1
                    elif sell_strat == "손절매":
                        new_order["desc"] = f"손절가 {fmt_p(s_p2)}{unit}"
                        new_order["qty"] = f"{s_q2:,}주"
                        new_order["target_price"] = s_p2
                    elif sell_strat == "트레일링 스탑":
                        new_order["desc"] = f"{fmt_p(s_base3)}{unit} 달성 후 최고점 대비 {s_drop3}%↓"
                        new_order["qty"] = f"{s_q3:,}주"
                        new_order["target_price"] = s_base3
                        
                    st.session_state.watch_orders.append(new_order)
                    st.success(f"[{name}] {sell_strat} 감시 등록.")


def render_order_status(symbol, name, c_price):
    st.markdown("<h4 style='color: #f39c12; margin-bottom: 15px;'>📋 실시간 감시 주문 현황</h4>", unsafe_allow_html=True)
    
    if not st.session_state.watch_orders:
        st.info("현재 등록된 감시 주문이 없습니다. 트레이딩 주문창에서 감시를 시작해보세요.")
    else:
        cols = st.columns([1, 1.5, 1.2, 1.5, 1, 2.5, 1.5, 0.8])
        cols[0].markdown("<small><b>시간</b></small>", unsafe_allow_html=True)
        cols[1].markdown("<small><b>종목</b></small>", unsafe_allow_html=True)
        cols[2].markdown("<small><b>구분</b></small>", unsafe_allow_html=True)
        cols[3].markdown("<small><b>전략</b></small>", unsafe_allow_html=True)
        cols[4].markdown("<small><b>수량</b></small>", unsafe_allow_html=True)
        cols[5].markdown("<small><b>상세 조건</b></small>", unsafe_allow_html=True)
        cols[6].markdown("<small><b>상태</b></small>", unsafe_allow_html=True)
        cols[7].markdown("<small><b>취소</b></small>", unsafe_allow_html=True)
        st.divider()

        for i, ord_item in enumerate(st.session_state.watch_orders):
            status_text = ord_item['status']
            if "target_price" in ord_item and ord_item['target_price'] > 0:
                item_c_price = StockDataLoader.get_current_price(ord_item['code'])
                if not item_c_price:
                    item_c_price = c_price
                t_p = ord_item['target_price']
                diff_pct = ((item_c_price / t_p) - 1) * 100
                if "매수" in ord_item['type']:
                    if diff_pct <= 0:
                        status_text = "🟢 타점!"
                    else:
                        status_text = f"🟡 {diff_pct:+.1f}%"
                else:
                    if diff_pct >= 0:
                        status_text = "🟢 타점!"
                    else:
                        status_text = f"🟡 {diff_pct:+.1f}%"

            r_cols = st.columns([1, 1.5, 1.2, 1.5, 1, 2.5, 1.5, 0.8])
            r_cols[0].markdown(f"<span style='font-size:0.85rem;'>{ord_item['time']}</span>", unsafe_allow_html=True)
            r_cols[1].markdown(f"<span style='font-size:0.85rem;'>{ord_item['name']}</span>", unsafe_allow_html=True)
            r_cols[2].markdown(f"<span style='font-size:0.85rem;'>{ord_item['type']}</span>", unsafe_allow_html=True)
            r_cols[3].markdown(f"<span style='font-size:0.85rem;'>{ord_item['strat']}</span>", unsafe_allow_html=True)
            r_cols[4].markdown(f"<span style='font-size:0.85rem;'>{ord_item['qty']}</span>", unsafe_allow_html=True)
            r_cols[5].markdown(f"<span style='font-size:0.85rem;'>{ord_item['desc']}</span>", unsafe_allow_html=True)
            
            color_tag = "#2ecc71" if "타점" in status_text else "#f1c40f"
            r_cols[6].markdown(f"<span style='font-size:0.85rem; color:{color_tag}; font-weight:bold;'>{status_text}</span>", unsafe_allow_html=True)
            
            if r_cols[7].button("❌", key=f"del_btn_{i}_{ord_item.get('id', 0)}", use_container_width=True):
                from supabase_db import SupabaseDB
                if ord_item.get("id"):
                    SupabaseDB.delete_watch_order(ord_item["id"])
                st.session_state.watch_orders.pop(i)
                st.success("감시 주문이 취소(삭제)되었습니다.")
                st.rerun()

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

