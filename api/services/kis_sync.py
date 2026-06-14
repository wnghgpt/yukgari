"""
KIS 체결 내역 → 매매일지 자동 동기화
- 평일 16:30 KST 자동 실행
- 당일 체결 내역 조회 → 감시/보유 일지에 tier별로 반영
"""
import os
import asyncio
from datetime import date, datetime, timezone, timedelta
from typing import Optional

KST = timezone(timedelta(hours=9))


# ── KIS 체결 내역 조회 ───────────────────────────────────────────────

def fetch_daily_fills(target_date: Optional[str] = None) -> list:
    """당일 체결 내역 조회 — 매수/매도 전체"""
    import requests
    from api.services.kis import _headers
    from config import KIS_VIRTUAL, KIS_SESSIONS

    if not KIS_SESSIONS:
        return []

    tr_id = "VTTC8001R" if KIS_VIRTUAL else "TTTC8001R"
    hdrs = _headers(tr_id)
    if not hdrs:
        return []

    acc = KIS_SESSIONS[0]["acc_no"]
    parts = acc.split("-")
    cano, acnt_cd = parts[0], (parts[1] if len(parts) > 1 else "01")
    d = target_date or date.today().strftime("%Y%m%d")

    from api.services.kis import _BASE
    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_cd,
        "INQR_STRT_DT": d,
        "INQR_END_DT": d,
        "SLL_BUY_DVSN_CD": "00",
        "INQR_DVSN": "00",
        "PDNO": "",
        "CCLD_DVSN": "01",
        "ORD_GNO_BRNO": "",
        "ODNO": "",
        "INQR_DVSN_3": "00",
        "INQR_DVSN_1": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    try:
        r = requests.get(
            f"{_BASE}/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
            headers=hdrs, params=params, timeout=10,
        )
        if r.status_code != 200:
            print(f"[Sync] 체결조회 오류 {r.status_code}: {r.text[:200]}")
            return []
        return r.json().get("output1") or []
    except Exception as e:
        print(f"[Sync] 체결조회 예외: {e}")
        return []


# ── tier 매칭 로직 ───────────────────────────────────────────────────

def _tier_filled_qty(executions: list, tier: int) -> int:
    return sum(e["qty"] for e in executions if e.get("tier") == tier)


def _next_open_tier(trade: dict, executions: list) -> Optional[int]:
    """수량이 아직 안 채워진 가장 낮은 tier 반환"""
    for tier in range(1, 5):
        planned = trade.get(f"entry{tier}_weight")
        if not planned:
            continue
        if _tier_filled_qty(executions, tier) < int(planned):
            return tier
    return None


def _calc_tier_avg(executions: list, tier: int) -> Optional[float]:
    fills = [e for e in executions if e.get("tier") == tier]
    if not fills:
        return None
    total_cost = sum(e["price"] * e["qty"] for e in fills)
    total_qty = sum(e["qty"] for e in fills)
    return round(total_cost / total_qty) if total_qty else None


def _is_tier_complete(trade: dict, executions: list, tier: int) -> bool:
    planned = trade.get(f"entry{tier}_weight")
    if not planned:
        return False
    return _tier_filled_qty(executions, tier) >= int(planned)


# ── 메인 동기화 ──────────────────────────────────────────────────────

async def sync_journal(user_id: str, target_date: Optional[str] = None):
    """체결 내역 → 해당 유저 일지 동기화"""
    from supabase_db import SupabaseDB

    fills = await asyncio.to_thread(fetch_daily_fills, target_date)
    if not fills:
        print(f"[Sync] 체결 내역 없음 (user={user_id})")
        return

    trades = await asyncio.to_thread(SupabaseDB.fetch_trades, user_id)
    active = [t for t in trades if t.get("result") in ("감시", "보유")]

    # ticker → active trade 매핑 (가장 최근 1개)
    trade_map: dict[str, dict] = {}
    for t in sorted(active, key=lambda x: x.get("date", ""), reverse=True):
        ticker = t.get("ticker", "")
        if ticker and ticker not in trade_map:
            trade_map[ticker] = t

    today_str = date.today().strftime("%Y-%m-%d")
    updated = 0

    for fill in fills:
        ticker = fill.get("pdno", "").strip()
        buy_sell = fill.get("sll_buy_dvsn_cd", "")  # "01"=매도 "02"=매수
        qty = int(fill.get("tot_ccld_qty") or 0)
        price = float(fill.get("avg_prvs") or fill.get("prpr") or 0)

        if not ticker or qty == 0 or price == 0:
            continue

        trade = trade_map.get(ticker)
        if not trade:
            print(f"[Sync] 일지 없는 종목 체결: {ticker} ({qty}주 @ {price})")
            continue

        trade_id = str(trade["id"])
        executions: list = list(trade.get("executions") or [])

        if buy_sell == "02":  # 매수
            _apply_buy(trade, executions, price, qty, today_str)
            new_result = "보유" if trade.get("result") == "감시" else trade.get("result")
        elif buy_sell == "01":  # 매도
            _apply_sell(trade, executions, price, qty, today_str)
            new_result = _determine_close_result(trade, executions)
        else:
            continue

        fields: dict = {"executions": executions}
        if new_result and new_result != trade.get("result"):
            fields["result"] = new_result
            if new_result in ("수익", "손절"):
                fields["exit_date"] = today_str

        await asyncio.to_thread(SupabaseDB.update_trade, trade_id, fields)
        print(f"[Sync] {ticker} 업데이트: {trade.get('result')} → {new_result or trade.get('result')}")
        updated += 1

    print(f"[Sync] 완료: {updated}건 업데이트 (user={user_id})")


def _apply_buy(trade: dict, executions: list, price: float, qty: int, date_str: str):
    """매수 체결을 tier에 할당 — 목표 수량 기준으로 순서대로 채움"""
    remaining = qty
    while remaining > 0:
        tier = _next_open_tier(trade, executions)
        if tier is None:
            print(f"[Sync] {trade.get('ticker')} 모든 tier 완료, 초과 매수 {remaining}주 무시")
            break
        planned = int(trade.get(f"entry{tier}_weight") or 0)
        already = _tier_filled_qty(executions, tier)
        can_fill = planned - already
        fill_qty = min(remaining, can_fill)
        executions.append({
            "tier": tier,
            "date": date_str,
            "price": price,
            "qty": fill_qty,
            "type": "buy",
        })
        remaining -= fill_qty


def _apply_sell(trade: dict, executions: list, price: float, qty: int, date_str: str):
    executions.append({
        "tier": 0,
        "date": date_str,
        "price": price,
        "qty": qty,
        "type": "sell",
    })


def _determine_close_result(trade: dict, executions: list) -> Optional[str]:
    """전량 매도 여부 확인 후 수익/손절 판정"""
    buy_qty = sum(e["qty"] for e in executions if e.get("type") == "buy")
    sell_qty = sum(e["qty"] for e in executions if e.get("type") == "sell")
    if sell_qty < buy_qty:
        return None  # 부분 매도, 아직 보유

    # 평균 매수가 vs 평균 매도가
    buy_cost = sum(e["price"] * e["qty"] for e in executions if e.get("type") == "buy")
    sell_cost = sum(e["price"] * e["qty"] for e in executions if e.get("type") == "sell")
    avg_buy = buy_cost / buy_qty if buy_qty else 0
    avg_sell = sell_cost / sell_qty if sell_qty else 0
    return "수익" if avg_sell >= avg_buy else "손절"


# ── 스케줄 루프 ──────────────────────────────────────────────────────

async def daily_sync_loop():
    """평일 16:30 KST 자동 동기화"""
    print("[Sync] 일지 자동 동기화 루프 시작")
    while True:
        now = datetime.now(KST)
        target = now.replace(hour=16, minute=30, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        while target.weekday() >= 5:
            target += timedelta(days=1)

        wait = (target - now).total_seconds()
        print(f"[Sync] 다음 동기화: {target.strftime('%Y-%m-%d %H:%M KST')} ({wait/3600:.1f}h 후)")
        await asyncio.sleep(wait)

        try:
            from supabase_db import SupabaseDB
            users = await asyncio.to_thread(SupabaseDB.fetch_all_users)
            for user in users:
                await sync_journal(user["id"])
        except Exception as e:
            print(f"[Sync] 루프 오류: {e}")
