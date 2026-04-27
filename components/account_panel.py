import streamlit as st
import os
from kis_client import KISClient

def render_account_panel(c_price):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    acc_options = []
    acc_map = {}
    for i in range(1, 5):
        k_no = os.getenv(f"KIS_ACC{i}_NO")
        k_name = os.getenv(f"KIS_ACC{i}_NAME", f"계좌 {i}")
        if k_no:
            label = f"{k_name} ({k_no})"
            acc_options.append(label)
            acc_map[label] = i
            
    if acc_options:
        default_idx = 0
        for idx, opt in enumerate(acc_options):
            if "46903020-01" in opt:
                default_idx = idx
                break
        selected_acc = st.selectbox("💳 조회 계좌 선택", options=acc_options, index=default_idx)
        acc_idx = acc_map[selected_acc]
    else:
        acc_idx = 4
        
    kis = KISClient(acc_idx=acc_idx)
    kis_data = kis.fetch_balance()
    
    if kis_data and kis_data.get("rt_cd") == "0":
        out1 = kis_data.get("output1", [])
        out2 = kis_data.get("output2", [{}])[0] if kis_data.get("output2") else {}
        
        yesu = int(out2.get("dnca_tot_amt", 0))
        tot_ev = int(out2.get("tot_evlu_amt", 0))
        tot_profit = int(out2.get("evlu_pfls_smtot_amt", 0))
        tot_pct = float(out2.get("evlu_erng_rt", 0))
        
        holdings = []
        for item in out1:
            if int(item.get("hldg_qty", 0)) > 0:
                holdings.append({
                    "name": item.get("prdt_name", "미상"),
                    "code": item.get("pdno", "000000"),
                    "qty": int(item.get("hldg_qty", 0)),
                    "avg": int(float(item.get("pchs_avg_pric", 0))),
                    "curr": int(item.get("prpr") or item.get("now_pric") or 0),
                    "profit": int(item.get("evlu_pfls_amt", 0)),
                    "pct": float(item.get("evlu_pfls_rt", 0))
                })

        with st.expander(f"💼 계좌 잔고 및 보유 종목", expanded=True):
            plus_ch = "+" if tot_profit >= 0 else ""
            st.markdown(f"<div style='font-size: 0.9rem; color: #d1d4dc; padding: 5px 0;'>💰 <b>예수금(D+2):</b> {yesu:,}원 &nbsp;&nbsp;|&nbsp;&nbsp; 📊 <b>총 평가:</b> {tot_ev:,}원 &nbsp;&nbsp;|&nbsp;&nbsp; 📈 <b>수익:</b> <span style='color: {'#ef5350' if tot_profit >= 0 else '#03A9F4'}; font-weight: bold;'>{plus_ch}{tot_profit:,}원 ({plus_ch}{tot_pct:.2f}%)</span></div>", unsafe_allow_html=True)
            st.divider()
            
            if not holdings:
                st.markdown("<div style='font-size:0.8rem; color:#8a8d9a; text-align:center; padding:20px;'>보유하신 국내 주식이 없습니다.</div>", unsafe_allow_html=True)
            else:
                th_style = "background-color: #f1f3f5; color: #000000; padding: 8px; font-size: 0.75rem; text-align: center; font-weight: bold;"
                td_style = "padding: 8px; font-size: 0.75rem; text-align: center; border-bottom: 1px solid #e9ecef; color: #000000;"
                
                table_html = f"""<table style='width: 100%; border-collapse: collapse; margin-top: 5px;'><thead><tr><th style='{th_style}'>종목명</th><th style='{th_style}'>수량</th><th style='{th_style}'>매입평단</th><th style='{th_style}'>현재가</th><th style='{th_style}'>평가손익</th><th style='{th_style}'>수익률</th></tr></thead><tbody>"""
                
                for item in holdings:
                    clr = "#ef5350" if item['pct'] >= 0 else "#03A9F4"
                    plus_sign = "+" if item['pct'] >= 0 else ""
                    table_html += f"<tr><td style='{td_style}'><b>{item['name']}</b><br><span style='color:#8a8d9a; font-size:0.6rem;'>{item['code']}</span></td><td style='{td_style}'>{item['qty']:,} 주</td><td style='{td_style}'>{item['avg']:,} 원</td><td style='{td_style}'>{item['curr']:,} 원</td><td style='{td_style} color:{clr};'>{plus_sign}{item['profit']:,} 원</td><td style='{td_style} color:{clr}; font-weight: bold;'>{plus_sign}{item['pct']:.2f}%</td></tr>"
                    
                table_html += "</tbody></table>"
                st.markdown(table_html, unsafe_allow_html=True)
    else:
        with st.expander(f"💼 한국투자증권 계좌 잔고 및 보유 종목", expanded=True):
            st.error("❌ 한국투자증권 API 연동 실패")
            if kis_data and kis_data.get("msg1"):
                st.warning(f"증권사 메시지: {kis_data.get('msg1').strip()}")
