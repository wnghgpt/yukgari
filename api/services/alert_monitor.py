"""
감시 종목 알림 서비스
- 일지에 result='감시' 로 저장된 종목을 실시간 가격에 따라 모니터링
- 진입가 근접 / 손절 / 목표가 도달 시 Telegram 전송
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


# ── 데이터 구조 ─────────────────────────────────────────────────────

@dataclass
class Alert:
    trade_id: str
    ticker: str
    entry_prices: list[float]       # [entry1, entry2, ...]
    stop_loss: float
    target_price: float
    user_id: str = ""
    triggered: set[str] = field(default_factory=set)  # "entry_0", "stop", "target"


_alerts: dict[str, list[Alert]] = {}   # symbol → [Alert, ...]


# ── 등록/해제 ────────────────────────────────────────────────────────

def _extract_entries(trade: dict) -> list[float]:
    result = []
    for i in range(1, 5):
        p = trade.get(f"entry{i}_price")
        if p:
            result.append(float(p))
    return result


def register_alert(trade: dict):
    tid    = str(trade.get("id", ""))
    ticker = (trade.get("ticker") or "").strip()
    if not ticker or not tid:
        return
    entries = _extract_entries(trade)
    sl  = float(trade.get("stop_loss")    or 0)
    tgt = float(trade.get("target_price") or 0)
    if not entries and sl == 0 and tgt == 0:
        return

    uid = str(trade.get("user_id") or "")
    alert = Alert(trade_id=tid, ticker=ticker, entry_prices=entries, stop_loss=sl, target_price=tgt, user_id=uid)
    _alerts.setdefault(ticker, [])
    _alerts[ticker] = [a for a in _alerts[ticker] if a.trade_id != tid]  # 중복 방지
    _alerts[ticker].append(alert)
    print(f"[Alert] 등록: {ticker} (id={tid}, 진입가={entries}, sl={sl}, tgt={tgt})")


def unregister_alert(trade_id: str):
    for sym in list(_alerts):
        _alerts[sym] = [a for a in _alerts[sym] if a.trade_id != str(trade_id)]
    print(f"[Alert] 해제: id={trade_id}")


WATCH_RESULTS = {"감시", "보유"}

def load_from_trades(trades: list[dict]):
    for t in trades:
        if t.get("result") in WATCH_RESULTS:
            register_alert(t)
    total = sum(len(v) for v in _alerts.values())
    print(f"[Alert] 시작 시 감시 로드: {total}건")


# ── 가격 수신 → 조건 체크 ────────────────────────────────────────────

async def _get_chat_id(user_id: str):
    if not user_id:
        return None
    try:
        from supabase_db import SupabaseDB
        user = await asyncio.to_thread(SupabaseDB.fetch_user, user_id)
        return user.get("telegram_chat_id") if user else None
    except Exception:
        return None


async def on_price(ticker: str, price: float):
    alerts = _alerts.get(ticker)
    if not alerts:
        return

    from api.services.telegram import send_message

    for alert in list(alerts):
        chat_id = await _get_chat_id(alert.user_id) if alert.user_id else None

        # 진입가 근접 (0.3% 이내) — 순서 보장: N차는 N-1차 이후에만 체크
        for i, ep in enumerate(alert.entry_prices):
            key = f"entry_{i}"
            if i > 0 and f"entry_{i-1}" not in alert.triggered:
                continue
            if key not in alert.triggered and ep > 0:
                if abs(price - ep) / ep <= 0.003:
                    alert.triggered.add(key)
                    ind = await _fetch_indicators(ticker)
                    asyncio.create_task(send_message(_msg_entry(alert, i + 1, ep, price, ind), chat_id=chat_id))

        # 손절가 도달
        if "stop" not in alert.triggered and alert.stop_loss > 0:
            if price <= alert.stop_loss:
                alert.triggered.add("stop")
                ind = await _fetch_indicators(ticker)
                asyncio.create_task(send_message(_msg_stop(alert, price, ind), chat_id=chat_id))

        # 목표가 도달
        if "target" not in alert.triggered and alert.target_price > 0:
            if price >= alert.target_price:
                alert.triggered.add("target")
                ind = await _fetch_indicators(ticker)
                asyncio.create_task(send_message(_msg_target(alert, price, ind), chat_id=chat_id))


# ── 보조지표 계산 ────────────────────────────────────────────────────

async def _fetch_indicators(ticker: str) -> dict:
    try:
        from api.routers.stock import get_indicators
        return await asyncio.to_thread(get_indicators, ticker)
    except Exception as e:
        print(f"[Alert] 지표 조회 오류: {e}")
        return {}


def _calc_rsi(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    ag = al = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        if d > 0: ag += d
        else:     al -= d
    ag /= period; al /= period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + (d if d > 0 else 0)) / period
        al = (al * (period - 1) + (-d if d < 0 else 0)) / period
    return round(100 - 100 / (1 + ag / al), 1) if al > 0 else 100.0


# ── 메시지 포맷 ──────────────────────────────────────────────────────

def _fmt(ticker: str, price: float) -> str:
    return f"{int(price):,}원" if ticker.isdigit() else f"${price:.2f}"


def _ind_lines(ind: dict) -> str:
    lines = []
    if ind.get("vol_ratio"):
        lines.append(f"거래량: 20평균 {ind['vol_ratio']:.0f}%")
    if ind.get("rsi") is not None:
        lines.append(f"RSI(14): {ind['rsi']}")
    if ind.get("alignment") and ind.get("all_mas"):
        label = ind["alignment"]
        all_mas = ind["all_mas"]
        sorted_mas = sorted(
            [(int(p), d["pct"]) for p, d in all_mas.items()],
            key=lambda x: x[1]
        )
        above_adj = next((m for m in reversed(sorted_mas) if m[1] < 0), None)
        below_adj = next((m for m in sorted_mas if m[1] > 0), None)
        chain = []
        current_inserted = False
        for period, pct in sorted_mas:
            if not current_inserted and pct > 0:
                chain.append("현")
                current_inserted = True
            if (period, pct) == above_adj:
                chain.append(f"{period}(+{abs(pct):.1f}%)")
            elif (period, pct) == below_adj:
                chain.append(f"{period}(-{pct:.1f}%)")
            else:
                chain.append(str(period))
        if not current_inserted:
            chain.append("현")
        prefix = f"{label}  " if label in ("정", "역") else ""
        lines.append(f"이평: {prefix}{' > '.join(chain)}")
    return "\n".join(lines)


def _msg_entry(alert: Alert, nth: int, ep: float, price: float, ind: dict) -> str:
    return (
        f"🟡 <b>{alert.ticker}</b> — {nth}차 진입가 근접\n"
        f"현재가: {_fmt(alert.ticker, price)}\n"
        f"진입가: {_fmt(alert.ticker, ep)}\n"
        f"{_ind_lines(ind)}\n"
        f"─────────\n"
        f"손절: {_fmt(alert.ticker, alert.stop_loss)}\n"
        f"목표: {_fmt(alert.ticker, alert.target_price)}"
    )


def _msg_stop(alert: Alert, price: float, ind: dict) -> str:
    return (
        f"🔴 <b>{alert.ticker}</b> — 손절가 도달\n"
        f"현재가: {_fmt(alert.ticker, price)}\n"
        f"손절가: {_fmt(alert.ticker, alert.stop_loss)}\n"
        f"{_ind_lines(ind)}"
    )


def _msg_target(alert: Alert, price: float, ind: dict) -> str:
    return (
        f"🟢 <b>{alert.ticker}</b> — 목표가 도달\n"
        f"현재가: {_fmt(alert.ticker, price)}\n"
        f"목표가: {_fmt(alert.ticker, alert.target_price)}\n"
        f"{_ind_lines(ind)}"
    )
