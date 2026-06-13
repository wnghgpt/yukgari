import io
import requests
from datetime import date, timedelta
from typing import Optional
import pandas as pd


def _latest_trading_day() -> str:
    d = date.today()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def _safe_float(v) -> Optional[float]:
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:
        return None


def _fmt_krw(v: float) -> str:
    v = int(v)
    if v >= 1_000_000_000_000:
        return f"{v / 1_000_000_000_000:.1f}조"
    if v >= 100_000_000:
        return f"{v / 100_000_000:.0f}억"
    return f"{v:,}"


def fetch_domestic_marcap(top_n: int = 100) -> list:
    """FDR KRX 캐시 CSV → 시가총액 상위 N개 (당일 종가 기준)"""
    trd = _latest_trading_day()
    url = (
        f"https://raw.githubusercontent.com/FinanceData/fdr_krx_data_cache"
        f"/refs/heads/master/data/listing/krx/{trd}.csv"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text), dtype={"Code": str})
    except Exception as e:
        print(f"[KRX] CSV 로드 오류: {e}")
        return []

    df = df.dropna(subset=["Marcap", "Code"])
    df = df[df["Marcap"] > 0]
    df = df.sort_values("Marcap", ascending=False).head(top_n).reset_index(drop=True)

    result = []
    for i, row in df.iterrows():
        marcap = _safe_float(row.get("Marcap"))
        price = _safe_float(row.get("Close"))
        change_pct = _safe_float(row.get("ChagesRatio"))
        result.append({
            "rank": int(i) + 1,
            "symbol": str(row["Code"]).strip(),
            "name": str(row["Name"]).strip(),
            "value": marcap or 0.0,
            "value_label": _fmt_krw(marcap or 0.0),
            "price": price,
            "change_pct": change_pct,
        })
    return result
