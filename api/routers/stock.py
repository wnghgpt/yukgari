from fastapi import APIRouter, HTTPException
from functools import lru_cache
from datetime import datetime, date
from data_loader import StockDataLoader

router = APIRouter()


@router.get("/ohlcv")
def get_ohlcv(symbol: str, count: int = 900, period: str = "D"):
    df = StockDataLoader.get_ohlcv(symbol, count, period)
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


@router.get("/price")
def get_price(symbol: str):
    price = StockDataLoader.get_current_price(symbol)
    prev_close = None
    try:
        df = StockDataLoader.get_ohlcv(symbol, count=2)
        if df is not None and len(df) >= 2:
            prev_close = float(df.iloc[-2]["Close"])
    except Exception:
        pass
    return {"symbol": symbol, "price": price, "prev_close": prev_close}


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

def _today() -> str:
    return date.today().isoformat()

def _current_hour() -> str:
    return datetime.now().strftime("%Y-%m-%d-%H")


@lru_cache(maxsize=4)
def _krx_listing_cached(hour: str):
    """FDR StockListing — 1시간 단위 캐시 (Marcap + Amount 모두 포함)"""
    import FinanceDataReader as fdr
    df = fdr.StockListing("KRX")
    if df is None or df.empty:
        return None
    return df


def _fmt_krw(v: float) -> str:
    v = int(v)
    if v >= 1_000_000_000_000:
        return f"{v / 1_000_000_000_000:.1f}조"
    if v >= 100_000_000:
        return f"{v / 100_000_000:.0f}억"
    return f"{v:,}"


def _build_ranking(sort_col: str, label_col: str, hour: str):
    df = _krx_listing_cached(hour)
    if df is None:
        return []
    df = df.dropna(subset=[sort_col])
    df = df[df[sort_col] > 0]
    df = df.sort_values(sort_col, ascending=False).head(100).reset_index(drop=True)

    result = []
    for i, row in df.iterrows():
        val = float(row[sort_col])
        result.append({
            "rank": int(i) + 1,
            "symbol": str(row["Code"]),
            "name": str(row["Name"]),
            "value": val,
            "value_label": _fmt_krw(val),
        })
    return result


@router.get("/ranking/marcap")
def ranking_marcap():
    return _build_ranking("Marcap", "Marcap", _current_hour())


@router.get("/ranking/trading")
def ranking_trading():
    return _build_ranking("Amount", "Amount", _current_hour())


# ── 해외 랭킹 ─────────────────────────────────────────────────────────

@lru_cache(maxsize=4)
def _nasdaq_listing_cached(hour: str):
    import FinanceDataReader as fdr
    df = fdr.StockListing("NASDAQ")
    if df is None or df.empty:
        return None
    return df


def _fmt_usd(v: float) -> str:
    if v >= 1_000_000_000_000:
        return f"${v / 1_000_000_000_000:.1f}T"
    if v >= 1_000_000_000:
        return f"${v / 1_000_000_000:.1f}B"
    if v >= 1_000_000:
        return f"${v / 1_000_000:.0f}M"
    return f"${v:,.0f}"


def _build_us_ranking(sort_col: str, hour: str):
    df = _nasdaq_listing_cached(hour)
    if df is None:
        return []
    col_map = {c.lower(): c for c in df.columns}
    actual_col = col_map.get(sort_col.lower())
    if not actual_col:
        return []
    df = df.dropna(subset=[actual_col])
    df[actual_col] = df[actual_col].apply(
        lambda x: float(str(x).replace("$", "").replace(",", "")) if isinstance(x, str) else float(x)
    )
    df = df[df[actual_col] > 0]
    df = df.sort_values(actual_col, ascending=False).head(100).reset_index(drop=True)
    result = []
    for i, row in df.iterrows():
        val = float(row[actual_col])
        sym = str(row.get("Symbol", row.get("symbol", "")))
        name = str(row.get("Name", sym))
        result.append({
            "rank": int(i) + 1,
            "symbol": sym,
            "name": name,
            "value": val,
            "value_label": _fmt_usd(val),
        })
    return result


@router.get("/ranking/us-marcap")
def ranking_us_marcap():
    return _build_us_ranking("MarketCap", _current_hour())


@router.get("/ranking/us-trading")
def ranking_us_trading():
    return _build_us_ranking("Volume", _current_hour())
