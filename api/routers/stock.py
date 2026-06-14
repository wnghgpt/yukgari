from fastapi import APIRouter, HTTPException
from datetime import datetime, date
import time as _time
from data_loader import StockDataLoader

_rank_cache: dict = {}
_TTL = {"dom_marcap": 86400, "dom_trading": 1800, "us_marcap": 1800, "us_trading": 1800}


def _cached_rank(key: str, fetch_fn):
    entry = _rank_cache.get(key)
    if entry:
        data, ts = entry
        if _time.time() - ts < _TTL.get(key, 1800):
            return data
    data = fetch_fn()
    if data:
        _rank_cache[key] = (data, _time.time())
    return data or []

router = APIRouter()


@router.get("/ohlcv")
def get_ohlcv(symbol: str, count: int = 900, period: str = "D"):
    df = StockDataLoader.get_ohlcv(_resolve_symbol(symbol), count, period)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No data")
    df["Date"] = df["Date"].astype(str)
    cols = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    return df[cols].to_dict(orient="records")


@router.get("/stock-info")
def get_stock_info(q: str):
    if not q:
        raise HTTPException(status_code=400, detail="q is required")
    return StockDataLoader.get_stock_info(q)


def _resolve_symbol(symbol: str) -> str:
    """한글 회사명이면 네이버 검색으로 종목코드 변환, 아니면 그대로 반환"""
    if any('가' <= c <= '힣' for c in symbol):
        try:
            results = StockDataLoader.search_stock_naver(symbol)
            if results:
                code = results[0].get('symbol', '')
                if code and code.isdigit():
                    return code
        except Exception:
            pass
    return symbol


@router.get("/price")
def get_price(symbol: str):
    actual = _resolve_symbol(symbol)
    price = StockDataLoader.get_current_price(actual)
    prev_close = None
    try:
        df = StockDataLoader.get_ohlcv(actual, count=2)
        if df is not None and len(df) >= 2:
            prev_close = float(df.iloc[-2]["Close"])
    except Exception:
        pass
    return {"symbol": symbol, "price": price, "prev_close": prev_close}


@router.get("/prices")
def get_prices(symbols: str):
    """콤마 구분 심볼 목록 일괄 현재가 조회"""
    sym_list = [s.strip() for s in symbols.split(',') if s.strip()]
    if not sym_list:
        return []

    def fetch_one(symbol: str):
        actual = _resolve_symbol(symbol)
        price = StockDataLoader.get_current_price(actual)
        prev_close = None
        try:
            df = StockDataLoader.get_ohlcv(actual, count=2)
            if df is not None and len(df) >= 2:
                prev_close = float(df.iloc[-2]["Close"])
        except Exception:
            pass
        return {"symbol": symbol, "price": price, "prev_close": prev_close}

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(len(sym_list), 8)) as ex:
        return list(ex.map(fetch_one, sym_list))


@router.get("/search")
def search(q: str):
    if not q:
        return []
    return StockDataLoader.search_stock_naver(q)


# ── indicators ─────────────────────────────────────────────────────

MA_PERIODS = [5, 20, 60, 120, 240]


def _calc_rsi(closes: list, period: int = 14):
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


def _ma_slope(closes: list, period: int) -> str:
    if len(closes) < period + 1:
        return "→"
    prev = sum(closes[-(period + 1):-1]) / period
    curr = sum(closes[-period:]) / period
    return "↗" if curr > prev else "↘"


@router.get("/indicators")
def get_indicators(symbol: str):
    df = StockDataLoader.get_ohlcv(symbol, 250, "D")
    if df is None or df.empty or len(df) < 30:
        raise HTTPException(status_code=404, detail="Not enough data")

    closes  = df["Close"].tolist()
    volumes = df["Volume"].tolist()
    current = closes[-1]

    # 거래량 비율
    vol_avg   = sum(volumes[-20:]) / min(len(volumes), 20)
    vol_ratio = round(volumes[-1] / vol_avg * 100) if vol_avg > 0 else 0

    # RSI
    rsi = _calc_rsi(closes)

    # 이평선
    mas = {p: sum(closes[-p:]) / p for p in MA_PERIODS if len(closes) >= p}

    # 배열 상태 (정/역/혼재)
    vals = [(p, mas[p]) for p in MA_PERIODS if p in mas]
    if len(vals) >= 2:
        is_jeong = all(vals[i][1] > vals[i + 1][1] for i in range(len(vals) - 1))
        is_yeok  = all(vals[i][1] < vals[i + 1][1] for i in range(len(vals) - 1))
        if is_jeong:
            alignment = "정"
            ma_order  = None
        elif is_yeok:
            alignment = "역"
            ma_order  = None
        else:
            alignment = "혼재"
            sorted_vals = sorted(vals, key=lambda x: x[1], reverse=True)
            ma_order = ">".join(str(p) for p, _ in sorted_vals)
    else:
        alignment = None
        ma_order  = None

    # 바로 위/아래 이평선 (현재가 기준)
    above_list = sorted([(p, v) for p, v in mas.items() if v < current], key=lambda x: x[1], reverse=True)
    below_list = sorted([(p, v) for p, v in mas.items() if v > current], key=lambda x: x[1])

    above_ma = below_ma = None
    if above_list:
        p, v = above_list[0]
        above_ma = {"period": p, "pct": round((current - v) / v * 100, 1), "slope": _ma_slope(closes, p)}
    if below_list:
        p, v = below_list[0]
        below_ma = {"period": p, "pct": round((current - v) / v * 100, 1), "slope": _ma_slope(closes, p)}

    all_mas = {
        str(p): {"pct": round((current - mas[p]) / mas[p] * 100, 1), "slope": _ma_slope(closes, p)}
        for p in MA_PERIODS if p in mas
    }

    return {
        "vol_ratio": vol_ratio,
        "rsi": rsi,
        "alignment": alignment,
        "ma_order": ma_order,
        "above_ma": above_ma,
        "below_ma": below_ma,
        "all_mas": all_mas,
    }


# ── ranking ────────────────────────────────────────────────────────

@router.get("/ranking/marcap")
def ranking_marcap():
    from api.services.krx import fetch_domestic_marcap
    return _cached_rank("dom_marcap", fetch_domestic_marcap)


@router.get("/ranking/trading")
def ranking_trading():
    from api.services.kis import fetch_domestic_trading
    return _cached_rank("dom_trading", fetch_domestic_trading)


@router.get("/ranking/us-marcap")
def ranking_us_marcap():
    from api.services.kis import fetch_overseas_marcap
    return _cached_rank("us_marcap", fetch_overseas_marcap)


@router.get("/ranking/us-trading")
def ranking_us_trading():
    from api.services.kis import fetch_overseas_trading
    return _cached_rank("us_trading", fetch_overseas_trading)
