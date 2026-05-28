import streamlit as st
import pandas as pd
from datetime import date
from supabase_db import SupabaseDB

PATTERNS = ["손잡이컵", "채널 돌파", "역추세 돌파 - 추세선 / 120선 / 목선", "돌파 후 풀백", "우량주 조정"]
RESULTS  = ["수익", "손절", "보유", "감시"]

# 프론트에서 계산하는 파생 컬럼 — DB 저장/비교에서 제외
FRONTEND_COMPUTED = {"avg_price", "profit_rate", "profit_amount", "holding_days"}

COL_CONFIG = {
    "id":               None,
    "created_at":       None,
    "date":             st.column_config.DateColumn("진입일", format="YYYY-MM-DD"),
    "exit_date":        st.column_config.DateColumn("청산일", format="YYYY-MM-DD"),
    "holding_days":     st.column_config.NumberColumn("보유(일)", disabled=True),
    "ticker":           st.column_config.TextColumn("종목"),
    "pattern":          st.column_config.SelectboxColumn("패턴", options=PATTERNS),
    "stages":           st.column_config.NumberColumn("단계", min_value=2, max_value=4, step=1),
    "channel_top":      st.column_config.NumberColumn("저항선"),
    "channel_bottom":   st.column_config.NumberColumn("지지선"),
    "entry1_price":     st.column_config.NumberColumn("1차가"),
    "entry1_weight":    st.column_config.NumberColumn("1차(주)"),
    "entry2_price":     st.column_config.NumberColumn("2차가"),
    "entry2_weight":    st.column_config.NumberColumn("2차(주)"),
    "entry3_price":     st.column_config.NumberColumn("3차가"),
    "entry3_weight":    st.column_config.NumberColumn("3차(주)"),
    "entry4_price":     st.column_config.NumberColumn("4차가"),
    "entry4_weight":    st.column_config.NumberColumn("4차(주)"),
    "stop_loss":        st.column_config.NumberColumn("손절선"),
    "target_price":     st.column_config.NumberColumn("목표가"),
    "result":           st.column_config.SelectboxColumn("결과", options=RESULTS),
    "avg_price":        st.column_config.NumberColumn("평균매수가", disabled=True),
    "exit1_price":      st.column_config.NumberColumn("청산1가"),
    "exit1_qty":        st.column_config.NumberColumn("청산1(주)"),
    "exit2_price":      st.column_config.NumberColumn("청산2가"),
    "exit2_qty":        st.column_config.NumberColumn("청산2(주)"),
    "profit_rate":      st.column_config.NumberColumn("수익률(%)", disabled=True, format="%.2f"),
    "profit_amount":    st.column_config.NumberColumn("수익금", disabled=True),
    "rebound_after_stop": st.column_config.CheckboxColumn("손절후반등"),
    "rebound_price":    st.column_config.NumberColumn("반등가"),
    "memo":             st.column_config.TextColumn("메모", width="large"),
}

COLUMN_ORDER = [
    "result", "date", "exit_date", "holding_days", "ticker", "pattern", "stages",
    "channel_top", "channel_bottom", "target_price",
    "entry1_price", "entry1_weight",
    "entry2_price", "entry2_weight",
    "entry3_price", "entry3_weight",
    "entry4_price", "entry4_weight",
    "stop_loss",
    "avg_price",
    "exit1_price", "exit1_qty",
    "exit2_price", "exit2_qty",
    "profit_rate", "profit_amount",
    "rebound_after_stop", "rebound_price",
    "memo",
]

# ── 프론트 계산 헬퍼 ────────────────────────────────────────

def _calc_avg_price(row):
    total_cost, total_qty = 0.0, 0.0
    for i in range(1, 5):
        try:
            p, q = float(row.get(f"entry{i}_price")), float(row.get(f"entry{i}_weight"))
            if p > 0 and q > 0:
                total_cost += p * q
                total_qty += q
        except (TypeError, ValueError):
            pass
    return total_cost / total_qty if total_qty > 0 else None

def _calc_exit_avg(row):
    items = []
    for i in range(1, 3):
        try:
            p, q = float(row.get(f"exit{i}_price")), float(row.get(f"exit{i}_qty"))
            if p > 0 and q > 0:
                items.append((p, q))
        except (TypeError, ValueError):
            pass
    if not items:
        return None, 0
    total_qty = sum(q for _, q in items)
    return sum(p * q for p, q in items) / total_qty, total_qty

def _calc_profit_rate(row):
    avg = row.get("avg_price")
    exit_avg, _ = _calc_exit_avg(row)
    try:
        return (float(exit_avg) - float(avg)) / float(avg) * 100
    except (TypeError, ValueError):
        return None

def _calc_profit_amount(row):
    avg = row.get("avg_price")
    exit_avg, exit_qty = _calc_exit_avg(row)
    try:
        return (float(exit_avg) - float(avg)) * exit_qty
    except (TypeError, ValueError):
        return None

def _calc_holding_days(row):
    entry_d = row.get("date")
    exit_d  = row.get("exit_date")
    if entry_d is None or (isinstance(entry_d, float) and pd.isna(entry_d)):
        return None
    end = exit_d if (exit_d is not None and not (isinstance(exit_d, float) and pd.isna(exit_d))) else date.today()
    try:
        return (end - entry_d).days
    except Exception:
        return None

# ── 데이터 로드 ─────────────────────────────────────────────

def _load():
    rows = SupabaseDB.fetch_trades()
    if not rows:
        df = pd.DataFrame(columns=["id", "created_at"] + COLUMN_ORDER)
    else:
        df = pd.DataFrame(rows)
    for col in COLUMN_ORDER:
        if col not in df.columns:
            df[col] = None
    for date_col in ["date", "exit_date"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.date

    if not df.empty:
        df["avg_price"]     = df.apply(_calc_avg_price, axis=1)
        df["profit_rate"]   = df.apply(_calc_profit_rate, axis=1)
        df["profit_amount"] = df.apply(_calc_profit_amount, axis=1)
        df["holding_days"]  = df.apply(_calc_holding_days, axis=1)

    if not df.empty and "result" in df.columns:
        result_order = {"보유": 0, "감시": 1, "수익": 2, "손절": 2}
        df["_sort_result"] = df["result"].map(result_order).fillna(3)
        df["_sort_date"]   = pd.to_datetime(df["exit_date"], errors="coerce")
        df = df.sort_values(["_sort_result", "_sort_date"], ascending=[True, False]).drop(
            columns=["_sort_result", "_sort_date"]
        )
    return df

def _refresh():
    st.session_state.trades_df = _load()
    st.session_state.trades_version = st.session_state.get("trades_version", 0) + 1

def _is_na(v):
    if v is None:
        return True
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):
        return False

def _val_equal(va, vb):
    a_na, b_na = _is_na(va), _is_na(vb)
    if a_na and b_na:
        return True
    if a_na != b_na:
        return False
    try:
        return va == vb
    except Exception:
        return str(va) == str(vb)

def _save_changes(original: pd.DataFrame, edited: pd.DataFrame, editor_state: dict):
    check_cols = [c for c in COLUMN_ORDER if c not in FRONTEND_COMPUTED]
    print(f"[SAVE] _save_changes called. rows={len(edited)}")

    for _, row in edited.iterrows():
        rid = row.get("id")
        payload = {k: v for k, v in row.to_dict().items() if k not in FRONTEND_COMPUTED}

        if _is_na(rid) or rid == "":
            if not _row_empty(row):
                print(f"[SAVE] INSERT: {row.get('ticker')}")
                SupabaseDB.insert_trade(payload)
        else:
            orig_matches = original[original["id"] == rid]
            if orig_matches.empty:
                print(f"[SAVE] original not found for id={rid}")
                continue
            orig_row = orig_matches.iloc[0]
            diff_cols = [
                col for col in check_cols
                if col in edited.columns and not _val_equal(orig_row.get(col), row.get(col))
            ]
            print(f"[SAVE] id={str(rid)[:8]} diff_cols={diff_cols}")
            if diff_cols:
                result = SupabaseDB.update_trade(str(rid), payload)
                print(f"[SAVE] update_trade result={result}")
                if not result:
                    st.error(f"DB 업데이트 실패: {str(rid)[:8]}")
                    return

    _refresh()
    st.rerun()

def _row_empty(row):
    check = ["ticker", "date", "pattern"]
    return all(pd.isna(row.get(c)) or row.get(c) == "" for c in check)

# ── 시뮬레이션에서 빠른 추가 ──────────────────────────────────

@st.dialog("📋 패턴 선택")
def quick_add_journal(payload: dict):
    st.markdown("<p style='font-size:0.85rem; margin:4px 0 8px;'>패턴을 선택하면 일지에 추가됩니다.</p>", unsafe_allow_html=True)
    pattern = st.selectbox("패턴", PATTERNS, label_visibility="collapsed")
    if st.button("추가", width="stretch", type="primary"):
        payload["pattern"] = pattern
        res, err = SupabaseDB.insert_trade(payload)
        if res:
            _refresh()
            st.rerun()
        else:
            st.error(f"저장 실패: {err}")

# ── 새 일지 폼 ───────────────────────────────────────────────

def _render_new_journal_form():
    def lbl(text):
        st.markdown(f"<p style='font-size:0.8rem; margin:4px 0 0; color:#d1d4dc;'>{text}</p>", unsafe_allow_html=True)
    def hr():
        st.markdown("<hr style='margin:8px 0; border-color:#2a2e39;'>", unsafe_allow_html=True)

    is_overseas = st.session_state.get("is_overseas", False)
    price_step = 0.1 if is_overseas else 100.0

    st.markdown("<div style='font-size:0.85rem; font-weight:bold; color:#3498DB; margin-bottom:6px;'>📝 새 일지</div>", unsafe_allow_html=True)

    a, b = st.columns([3, 7])
    with a: lbl("결과")
    with b: result = st.selectbox("결과", RESULTS, key="nj_result", label_visibility="collapsed")

    is_done = result in ["수익", "손절"]

    a, b = st.columns([3, 7])
    with a: lbl("진입일")
    with b: d = st.date_input("진입일", value=date.today(), key="nj_date", label_visibility="collapsed")

    if is_done:
        a, b = st.columns([3, 7])
        with a: lbl("청산일")
        with b: exit_date = st.date_input("청산일", value=None, key="nj_exit_date", label_visibility="collapsed")
    else:
        exit_date = None

    a, b = st.columns([3, 7])
    with a: lbl("종목")
    with b: ticker = st.text_input("종목", key="nj_ticker", label_visibility="collapsed")

    a, b = st.columns([3, 7])
    with a: lbl("패턴")
    with b: pattern = st.selectbox("패턴", PATTERNS, key="nj_pattern", label_visibility="collapsed")

    hr()

    a, b = st.columns([3, 7])
    with a: lbl("저항선")
    with b:
        if "nj_ct" not in st.session_state:
            st.session_state["nj_ct"] = 0.0
        channel_top = st.number_input("저항선", step=price_step, key="nj_ct", label_visibility="collapsed")

    ct_prev = st.session_state.get("nj_ct_prev", 0.0)
    if channel_top != ct_prev:
        if st.session_state.get("nj_cb", 0.0) == ct_prev:
            st.session_state["nj_cb"] = channel_top
        st.session_state["nj_ct_prev"] = channel_top

    a, b = st.columns([3, 7])
    with a: lbl("지지선")
    with b:
        if "nj_cb" not in st.session_state:
            st.session_state["nj_cb"] = 0.0
        channel_bottom = st.number_input("지지선", step=price_step, key="nj_cb", label_visibility="collapsed")

    if pattern in ["손잡이컵", "채널 돌파", "역추세 돌파 - 추세선 / 120선 / 목선"]:
        stages = 2
    else:
        if channel_top > 0 and channel_bottom > 0 and channel_top > channel_bottom:
            width_pct = (channel_top - channel_bottom) / channel_bottom * 100
            stages = 3 if width_pct <= 10 else 4
            st.markdown(f"<p style='font-size:0.7rem; color:#8a8d9a; margin:2px 0;'>채널 폭 {width_pct:.1f}% → {stages}단계</p>", unsafe_allow_html=True)
        else:
            stages = 3

    hr()

    a, b = st.columns([3, 7])
    with a: st.markdown("<p style='font-size:0.7rem; color:#8a8d9a; margin:2px 0;'>차수</p>", unsafe_allow_html=True)
    with b:
        c1, c2 = st.columns(2)
        with c1: st.markdown("<p style='font-size:0.7rem; color:#8a8d9a; margin:2px 0;'>가격</p>", unsafe_allow_html=True)
        with c2: st.markdown("<p style='font-size:0.7rem; color:#8a8d9a; margin:2px 0;'>수량(주)</p>", unsafe_allow_html=True)

    entries = []
    for i in range(stages):
        a, b = st.columns([3, 7])
        with a: lbl(f"{i+1}차")
        with b:
            c1, c2 = st.columns(2)
            with c1: ep = st.number_input(f"가격{i+1}", value=0.0, step=price_step, key=f"nj_ep{i}_{stages}", label_visibility="collapsed")
            with c2: ew = st.number_input(f"수량{i+1}", value=0, step=1, key=f"nj_ew{i}_{stages}", label_visibility="collapsed")
        entries.append((ep, ew))

    hr()

    a, b = st.columns([3, 7])
    with a: lbl("손절선")
    with b: stop_loss = st.number_input("손절선", value=0.0, step=price_step, key="nj_stop_loss", label_visibility="collapsed")

    a, b = st.columns([3, 7])
    with a: lbl("목표가")
    with b: target_price = st.number_input("목표가", value=0.0, step=price_step, key="nj_target_price", label_visibility="collapsed")

    if is_done:
        hr()
        a, b = st.columns([3, 7])
        with a: lbl("청산1가")
        with b: exit1_price = st.number_input("청산1가", value=0.0, step=price_step, key="nj_exit1_price", label_visibility="collapsed")

        a, b = st.columns([3, 7])
        with a: lbl("청산1(주)")
        with b: exit1_qty = st.number_input("청산1(주)", value=0, step=1, key="nj_exit1_qty", label_visibility="collapsed")

        a, b = st.columns([3, 7])
        with a: lbl("청산2가")
        with b: exit2_price = st.number_input("청산2가", value=0.0, step=price_step, key="nj_exit2_price", label_visibility="collapsed")

        a, b = st.columns([3, 7])
        with a: lbl("청산2(주)")
        with b: exit2_qty = st.number_input("청산2(주)", value=0, step=1, key="nj_exit2_qty", label_visibility="collapsed")

        a, b = st.columns([3, 7])
        with a: lbl("손절후반등")
        with b: rebound = st.checkbox("손절 후 반등", key="nj_rebound", label_visibility="collapsed")

        rebound_price = None
        if rebound:
            a, b = st.columns([3, 7])
            with a: lbl("반등가")
            with b: rebound_price = st.number_input("반등가", value=0.0, step=price_step, key="nj_rebound_price", label_visibility="collapsed")
    else:
        exit1_price = exit1_qty = exit2_price = exit2_qty = None
        rebound = False
        rebound_price = None

    memo = st.text_area("메모", height=60, key="nj_memo", label_visibility="collapsed", placeholder="메모")

    if st.button("저장", width="stretch", type="primary", key="nj_save"):
        if not st.session_state.get("nj_ticker", "").strip():
            st.warning("종목코드를 입력해주세요.")
            return
        payload = {
            "date": str(d),
            "exit_date": str(exit_date) if exit_date else None,
            "ticker": ticker.upper(),
            "pattern": pattern,
            "stages": stages,
            "channel_top": channel_top or None,
            "channel_bottom": channel_bottom or None,
            "stop_loss": stop_loss or None,
            "target_price": target_price or None,
            "exit1_price": exit1_price or None,
            "exit1_qty": int(exit1_qty) if exit1_qty else None,
            "exit2_price": exit2_price or None,
            "exit2_qty": int(exit2_qty) if exit2_qty else None,
            "result": result,
            "rebound_after_stop": rebound,
            "rebound_price": rebound_price,
            "memo": memo or None,
        }
        for i, (ep, ew) in enumerate(entries):
            payload[f"entry{i+1}_price"] = ep or None
            payload[f"entry{i+1}_weight"] = ew or None

        res, err = SupabaseDB.insert_trade(payload)
        if res:
            for k in [k for k in st.session_state if k.startswith("nj_")]:
                del st.session_state[k]
            _refresh()
            st.rerun()
        else:
            st.error(f"저장 실패: {err}")


# ── 요약 카드 ────────────────────────────────────────────────

def _render_summary_card(df: pd.DataFrame):
    is_overseas = st.session_state.get("is_overseas", False)

    closed   = df[df["result"].isin(["수익", "손절"])]
    wins     = df[df["result"] == "수익"]
    losses   = df[df["result"] == "손절"]
    n_hold   = len(df[df["result"] == "보유"])
    n_watch  = len(df[df["result"] == "감시"])
    n_closed = len(closed)
    win_rate = len(wins) / n_closed * 100 if n_closed > 0 else 0

    avg_win  = wins["profit_rate"].dropna().mean() if not wins.empty else 0
    avg_loss = losses["profit_rate"].dropna().mean() if not losses.empty else 0
    rr = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    net_pnl = closed["profit_amount"].dropna().sum() if "profit_amount" in closed.columns else 0
    net_pnl_str = f"+{net_pnl/10000:.0f}만" if net_pnl >= 0 else f"{net_pnl/10000:.0f}만"
    net_color = "#2ecc71" if net_pnl >= 0 else "#ef5350"

    rebound_total = len(losses)
    rebound_cnt = int(losses["rebound_after_stop"].sum()) if "rebound_after_stop" in losses.columns else 0
    rebound_pct = rebound_cnt / rebound_total * 100 if rebound_total > 0 else 0
    rebound_color = "#e67e22" if rebound_pct >= 30 else "#8a8d9a"

    with st.container(border=True):
        c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 1.5, 2, 2, 2.5, 3, 3])
        with c1:
            st.markdown(f"<div style='font-size:0.75rem; color:#8a8d9a;'>보유</div><div style='font-size:1rem; font-weight:bold;'>{n_hold}</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div style='font-size:0.75rem; color:#8a8d9a;'>감시</div><div style='font-size:1rem; font-weight:bold;'>{n_watch}</div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div style='font-size:0.75rem; color:#8a8d9a;'>거래</div><div style='font-size:1rem; font-weight:bold;'>{n_closed}건</div>", unsafe_allow_html=True)
        with c4:
            wr_color = "#2ecc71" if win_rate >= 50 else "#ef5350"
            st.markdown(f"<div style='font-size:0.75rem; color:#8a8d9a;'>승률</div><div style='font-size:1rem; font-weight:bold; color:{wr_color};'>{win_rate:.0f}%</div>", unsafe_allow_html=True)
        with c5:
            rr_color = "#2ecc71" if rr >= 1 else "#ef5350"
            st.markdown(f"<div style='font-size:0.75rem; color:#8a8d9a;'>손익비</div><div style='font-size:1rem; font-weight:bold; color:{rr_color};'>{rr:.1f}x</div>", unsafe_allow_html=True)
        with c6:
            st.markdown(f"<div style='font-size:0.75rem; color:#8a8d9a;'>순손익</div><div style='font-size:1rem; font-weight:bold; color:{net_color};'>{net_pnl_str}</div>", unsafe_allow_html=True)
        with c7:
            st.markdown(f"<div style='font-size:0.75rem; color:#8a8d9a;'>손절후반등</div><div style='font-size:1rem; font-weight:bold; color:{rebound_color};'>{rebound_cnt}/{rebound_total} ({rebound_pct:.0f}%)</div>", unsafe_allow_html=True)

        st.markdown("<hr style='margin:8px 0; border-color:#2a2e39;'>", unsafe_allow_html=True)

        pattern_cols = st.columns(len(PATTERNS))
        short_names = {
            "손잡이컵": "손잡이컵",
            "채널 돌파": "채널돌파",
            "역추세 돌파 - 추세선 / 120선 / 목선": "역추세돌파",
            "돌파 후 풀백": "돌파후풀백",
            "우량주 조정": "우량주조정",
        }
        for pat, col in zip(PATTERNS, pattern_cols):
            pat_df = closed[closed["pattern"] == pat]
            pat_wins = len(pat_df[pat_df["result"] == "수익"])
            pat_total = len(pat_df)
            with col:
                if pat_total > 0:
                    pr = pat_wins / pat_total * 100
                    p_color = "#2ecc71" if pr >= 50 else "#ef5350"
                    st.markdown(f"<div style='font-size:0.7rem; color:#8a8d9a;'>{short_names[pat]}</div><div style='font-size:0.85rem; font-weight:bold; color:{p_color};'>{pr:.0f}% <span style='font-size:0.65rem; color:#555e6e;'>({pat_total}건)</span></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='font-size:0.7rem; color:#8a8d9a;'>{short_names[pat]}</div><div style='font-size:0.85rem; color:#444;'>-</div>", unsafe_allow_html=True)


# ── 메인 렌더 ────────────────────────────────────────────────

def render_trade_journal():
    if "trades_df" not in st.session_state:
        st.session_state.trades_df = _load()
    if "trades_version" not in st.session_state:
        st.session_state.trades_version = 0

    original = st.session_state.trades_df.copy()
    display_cols = [c for c in COLUMN_ORDER if c in original.columns]
    editor_key = f"trades_editor_{st.session_state.trades_version}"

    editor_state = st.session_state.get(editor_key, {})
    has_pending = bool(editor_state.get("edited_rows") or editor_state.get("added_rows"))

    journal_col, form_col = st.columns([7, 3])

    with journal_col:
        st.markdown("<h4 style='margin-bottom:6px;'>📒 매매 일지</h4>", unsafe_allow_html=True)
        _render_summary_card(original)

        if has_pending:
            st.markdown("""
            <style>
            button[data-testid="baseButton-primary"] {
                background-color: #c0392b !important;
                border-color: #c0392b !important;
            }
            button[data-testid="baseButton-primary"]:hover {
                background-color: #e74c3c !important;
                border-color: #e74c3c !important;
            }
            </style>
            """, unsafe_allow_html=True)

        col_save, _ = st.columns([2, 8])
        with col_save:
            save_clicked = st.button("💾 변경사항 저장", disabled=not has_pending, type="primary", width="stretch")

        edited = st.data_editor(
            original[display_cols] if not original.empty else pd.DataFrame(columns=display_cols),
            column_config=COL_CONFIG,
            num_rows="dynamic",
            width="stretch",
            height=400,
            key=editor_key,
        )

        deleted_indices = editor_state.get("deleted_rows", [])
        if deleted_indices:
            for idx in deleted_indices:
                if idx < len(original):
                    rid = original.iloc[idx].get("id")
                    if rid and not pd.isna(rid):
                        SupabaseDB.delete_trade(str(rid))
            _refresh()
            st.rerun()

        if "id" in original.columns:
            edited["id"] = original["id"].values[:len(edited)] if len(edited) <= len(original) else \
                list(original["id"].values) + [None] * (len(edited) - len(original))

        if save_clicked:
            _save_changes(original, edited, editor_state)

    with form_col:
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            _render_new_journal_form()
