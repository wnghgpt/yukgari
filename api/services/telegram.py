import asyncio
import requests
from datetime import datetime, timezone, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

KST = timezone(timedelta(hours=9))


async def send_message(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] 설정 없음 — .env 에 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 입력 필요")
        return False

    def _post():
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        return resp.status_code == 200

    try:
        return await asyncio.to_thread(_post)
    except Exception as e:
        print(f"[Telegram] 전송 오류: {e}")
        return False


# ── 포맷 헬퍼 ────────────────────────────────────────────────────────

def _is_kr(ticker: str) -> bool:
    return ticker.isdigit()


def _fmt(ticker: str, price: float) -> str:
    return f"{int(price):,}원" if _is_kr(ticker) else f"${price:.2f}"


def _calc_avg_price(trade: dict) -> float | None:
    """분할매수 가중평균단가 (entry_weight 필드에 주수가 저장됨)"""
    total_cost = total_qty = 0.0
    for i in range(1, 5):
        p = trade.get(f"entry{i}_price")
        q = trade.get(f"entry{i}_weight")
        if p and q:
            total_cost += float(p) * float(q)
            total_qty += float(q)
    return total_cost / total_qty if total_qty else None


def _calc_loss_pct(trade: dict) -> float | None:
    """실손실률: (평균단가 - 손절가) / 평균단가 × 100"""
    avg = _calc_avg_price(trade)
    sl = trade.get("stop_loss")
    if avg is None or not sl or avg == 0:
        return None
    return (avg - float(sl)) / avg * 100


# ── 감시 추가 즉시 알림 ───────────────────────────────────────────────

def format_watch_alert(trade: dict) -> str:
    ticker = trade.get("ticker", "")
    name = trade.get("name") or ticker
    pattern = trade.get("pattern", "")
    stages = trade.get("stages", 0)
    stop_loss = trade.get("stop_loss")
    target_price = trade.get("target_price")
    channel_top = trade.get("channel_top")
    channel_bottom = trade.get("channel_bottom")
    memo = trade.get("memo")

    icons = ["🟢", "🟡", "🔴", "⚫"]
    entry_lines = []
    for i in range(1, 5):
        p = trade.get(f"entry{i}_price")
        q = trade.get(f"entry{i}_weight")
        if p:
            qty_str = f" × {int(float(q))}주" if q else ""
            entry_lines.append(f"{icons[i-1]} {i}차: {_fmt(ticker, float(p))}{qty_str}")

    loss_pct = _calc_loss_pct(trade)
    div = "━━━━━━━━━━━━━━━━"

    lines = [
        "📋 감시 종목 추가",
        div,
        f"📌 <b>{name}</b> ({ticker})",
        f"📊 패턴: {pattern} | {stages}단계",
        div,
        *entry_lines,
        div,
    ]
    if loss_pct is not None:
        lines.append(f"📉 실손실률: -{loss_pct:.1f}%")
    if stop_loss:
        lines.append(f"⛔ 손절가:   {_fmt(ticker, float(stop_loss))}")
    if target_price:
        lines.append(f"🎯 목표가:   {_fmt(ticker, float(target_price))}")
    if channel_top or channel_bottom:
        top_str = _fmt(ticker, float(channel_top)) if channel_top else "—"
        bot_str = _fmt(ticker, float(channel_bottom)) if channel_bottom else "—"
        lines.append(f"📐 저항: {top_str} | 지지: {bot_str}")
    if memo:
        lines.append(f"💬 {memo}")

    return "\n".join(lines)


# ── 정기 요약 (8시/14시 KST) ─────────────────────────────────────────

async def send_daily_summary():
    from supabase_db import SupabaseDB
    from data_loader import StockDataLoader

    trades = await asyncio.to_thread(SupabaseDB.fetch_trades)
    watch_trades = [t for t in trades if t.get("result") == "감시"]
    if not watch_trades:
        return

    # 현재가 + 전일 종가 조회
    prices: dict[str, float] = {}
    prev_closes: dict[str, float] = {}
    for t in watch_trades:
        sym = t["ticker"]
        try:
            p = await asyncio.to_thread(StockDataLoader.get_current_price, sym)
            if p:
                prices[sym] = float(p)
            df = await asyncio.to_thread(StockDataLoader.get_ohlcv, sym, 2)
            if df is not None and len(df) >= 2:
                prev_closes[sym] = float(df.iloc[-2]["Close"])
        except Exception:
            pass

    now_kst = datetime.now(KST)
    hour_str = "08:00" if now_kst.hour < 12 else "14:00"
    today = now_kst.date()
    div = "━━━━━━━━━━━━"

    lines = [f"📊 감시 요약 {hour_str} KST | {len(watch_trades)}종목"]

    for idx, trade in enumerate(watch_trades, 1):
        ticker = trade["ticker"]
        pattern = trade.get("pattern", "")

        # D+n
        try:
            d_days = (today - datetime.strptime(trade["date"], "%Y-%m-%d").date()).days
            d_str = f"D+{d_days}"
        except Exception:
            d_str = ""

        # 현재가 + 등락률
        current = prices.get(ticker)
        prev = prev_closes.get(ticker)
        if current:
            price_str = _fmt(ticker, current)
            if prev and prev > 0:
                chg = (current - prev) / prev * 100
                sign = "+" if chg >= 0 else ""
                price_str += f" ({sign}{chg:.1f}%)"
        else:
            price_str = "—"

        # 1차까지 거리 (현재가가 1차 매수가보다 위에 있을 때만)
        entry1 = trade.get("entry1_price")
        gap_str = ""
        if current and entry1 and float(entry1) > 0 and current > float(entry1):
            gap = (float(entry1) - current) / current * 100
            gap_str = f" | 1차까지 {gap:.1f}%"

        # 분할매수 가격(주수)
        entries = []
        for i in range(1, 5):
            p = trade.get(f"entry{i}_price")
            q = trade.get(f"entry{i}_weight")
            if p:
                q_str = f"({int(float(q))}주)" if q else ""
                entries.append(f"{_fmt(ticker, float(p))}{q_str}")
        entry_str = " / ".join(entries)

        loss_pct = _calc_loss_pct(trade)
        loss_str = f"손실률 -{loss_pct:.1f}% | " if loss_pct is not None else ""
        stop_loss = trade.get("stop_loss")
        target = trade.get("target_price")
        sl_str = _fmt(ticker, float(stop_loss)) if stop_loss else "—"
        tgt_str = _fmt(ticker, float(target)) if target else "—"

        lines += [
            div,
            f"{idx}. <b>{ticker}</b> | {pattern} {d_str}",
            f"   현재가 {price_str}{gap_str}",
            f"   매수: {entry_str}",
            f"   {loss_str}손절 {sl_str} | 목표 {tgt_str}",
        ]

    lines.append(div)
    await send_message("\n".join(lines))
