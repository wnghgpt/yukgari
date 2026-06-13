import os
import time
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

_BASE = "https://openapi.koreainvestment.com:9443"
_token_cache: dict = {}


def _app_credentials():
    for idx in [4, 1, 2, 3]:
        key = os.getenv(f"KIS_ACC{idx}_KEY")
        secret = os.getenv(f"KIS_ACC{idx}_SECRET")
        if key and secret:
            return key, secret
    return None, None


def _get_token() -> Optional[str]:
    app_key, app_secret = _app_credentials()
    if not app_key:
        return None
    cached = _token_cache.get("t")
    if cached and time.time() - cached["ts"] < 3500:
        return cached["v"]
    try:
        r = requests.post(
            f"{_BASE}/oauth2/tokenP",
            headers={"Content-Type": "application/json"},
            json={"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret},
            timeout=5,
        )
        if r.status_code == 200:
            tok = r.json().get("access_token")
            _token_cache["t"] = {"v": tok, "ts": time.time()}
            return tok
        print(f"[KIS] token error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[KIS] token exception: {e}")
    return None


def _headers(tr_id: str) -> Optional[dict]:
    app_key, app_secret = _app_credentials()
    tok = _get_token()
    if not tok:
        return None
    return {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {tok}",
        "appKey": app_key,
        "appSecret": app_secret,
        "tr_id": tr_id,
        "custtype": "P",
    }


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(str(v).replace(",", "").strip())
        return None if f != f else f  # NaN check
    except Exception:
        return None


def _fmt_krw(v: float) -> str:
    v = int(v)
    if v >= 1_000_000_000_000:
        return f"{v / 1_000_000_000_000:.1f}조"
    if v >= 100_000_000:
        return f"{v / 100_000_000:.0f}억"
    return f"{v:,}"


def _fmt_usd(v: float) -> str:
    if v >= 1_000_000_000_000:
        return f"${v / 1_000_000_000_000:.1f}T"
    if v >= 1_000_000_000:
        return f"${v / 1_000_000_000:.1f}B"
    if v >= 1_000_000:
        return f"${v / 1_000_000:.0f}M"
    return f"${v:,.0f}"


def fetch_domestic_marcap() -> list:
    """국내 시가총액 상위 100 (FHPST01740000)"""
    hdrs = _headers("FHPST01740000")
    if not hdrs:
        return []
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_cond_scr_div_code": "20174",
        "fid_input_iscd": "0000",
        "fid_div_cls_code": "0",
        "fid_blng_cls_code": "0",
        "fid_trgt_cls_code": "111111111",
        "fid_trgt_exls_cls_code": "0000000000",
        "fid_input_price_1": "",
        "fid_input_price_2": "",
        "fid_vol_cnt": "",
        "fid_input_date_1": "",
    }
    try:
        r = requests.get(
            f"{_BASE}/uapi/domestic-stock/v1/ranking/market-cap",
            headers=hdrs, params=params, timeout=10,
        )
        if r.status_code != 200:
            print(f"[KIS] domestic marcap {r.status_code}: {r.text[:300]}")
            return []
        items = r.json().get("output", [])
        result = []
        for i, item in enumerate(items[:100]):
            price = _safe_float(item.get("stck_prpr"))
            marcap = _safe_float(item.get("stck_avls") or item.get("mksc_stck_totv"))
            change_pct = _safe_float(item.get("prdy_ctrt"))
            result.append({
                "rank": i + 1,
                "symbol": item.get("mksc_shrn_iscd", "").strip(),
                "name": item.get("hts_kor_isnm", "").strip(),
                "value": marcap or 0.0,
                "value_label": _fmt_krw(marcap or 0.0),
                "price": price,
                "change_pct": change_pct,
            })
        return result
    except Exception as e:
        print(f"[KIS] domestic marcap exception: {e}")
        return []


def fetch_domestic_trading() -> list:
    """국내 거래량 상위 100 (FHPST01720000) — 거래대금 = acml_vol × stck_prpr"""
    hdrs = _headers("FHPST01720000")
    if not hdrs:
        return []
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_cond_scr_div_code": "20171",
        "fid_input_iscd": "0000",
        "fid_div_cls_code": "0",
        "fid_trgt_cls_code": "111111111",
        "fid_trgt_exls_cls_code": "0000000000",
        "fid_input_price_1": "",
        "fid_input_price_2": "",
        "fid_vol_cnt": "",
        "fid_input_date_1": "",
        "fid_rank_sort_cls_code": "0",
    }
    try:
        r = requests.get(
            f"{_BASE}/uapi/domestic-stock/v1/quotations/volume-rank",
            headers=hdrs, params=params, timeout=10,
        )
        if r.status_code != 200:
            print(f"[KIS] domestic trading {r.status_code}: {r.text[:300]}")
            return []
        items = r.json().get("output", [])
        result = []
        for i, item in enumerate(items[:100]):
            price = _safe_float(item.get("stck_prpr"))
            vol = _safe_float(item.get("acml_vol"))
            amount = (price * vol) if price and vol else None
            change_pct = _safe_float(item.get("prdy_ctrt"))
            result.append({
                "rank": i + 1,
                "symbol": item.get("mksc_shrn_iscd", "").strip(),
                "name": item.get("hts_kor_isnm", "").strip(),
                "value": amount or 0.0,
                "value_label": _fmt_krw(amount or 0.0),
                "price": price,
                "change_pct": change_pct,
            })
        return result
    except Exception as e:
        print(f"[KIS] domestic trading exception: {e}")
        return []


def fetch_overseas_marcap(excd: str = "NAS") -> list:
    """해외 시가총액 상위 (HHDFS76350100)"""
    hdrs = _headers("HHDFS76350100")
    if not hdrs:
        return []
    params = {"AUTH": "", "EXCD": excd, "SYMB": "", "KEYB": "", "CURR_GB": "0", "VOL_RANG": "0"}
    try:
        r = requests.get(
            f"{_BASE}/uapi/overseas-stock/v1/ranking/market-cap",
            headers=hdrs, params=params, timeout=10,
        )
        if r.status_code != 200:
            print(f"[KIS] overseas marcap {r.status_code}: {r.text[:300]}")
            return []
        items = r.json().get("output", [])
        result = []
        for i, item in enumerate(items[:100]):
            price = _safe_float(item.get("last") or item.get("nxol") or item.get("stck_prpr"))
            marcap = _safe_float(item.get("marc") or item.get("mktv") or item.get("mksc_stck_totv"))
            change_pct = _safe_float(item.get("rate") or item.get("chgr") or item.get("prdy_ctrt"))
            sym = (item.get("symb") or item.get("stck_shrn_iscd") or item.get("rsym") or "").strip()
            name = (item.get("name") or item.get("hts_kor_isnm") or sym).strip()
            result.append({
                "rank": i + 1,
                "symbol": sym,
                "name": name,
                "value": marcap or 0.0,
                "value_label": _fmt_usd(marcap or 0.0),
                "price": price,
                "change_pct": change_pct,
            })
        return result
    except Exception as e:
        print(f"[KIS] overseas marcap exception: {e}")
        return []


def fetch_overseas_trading(excd: str = "NAS") -> list:
    """해외 거래대금 상위 (HHDFS76320010) — 정확한 경로 미확인, marcap 경로 재시도"""
    hdrs = _headers("HHDFS76320010")
    if not hdrs:
        return []
    params = {"AUTH": "", "EXCD": excd, "SYMB": "", "KEYB": "", "CURR_GB": "0", "VOL_RANG": "0"}
    # NOTE: 해당 TR_ID의 정확한 REST 경로를 찾지 못함. 동일 base로 시도.
    for path in [
        "/uapi/overseas-stock/v1/ranking/trade-amount",
        "/uapi/overseas-stock/v1/ranking/market-cap",
    ]:
        try:
            r = requests.get(f"{_BASE}{path}", headers=hdrs, params=params, timeout=10)
            if r.status_code != 200:
                continue
            items = r.json().get("output", [])
            if not items:
                continue
            result = []
            for i, item in enumerate(items[:100]):
                price = _safe_float(item.get("last") or item.get("nxol") or item.get("stck_prpr"))
                amount = _safe_float(item.get("tamt") or item.get("marc") or item.get("acml_tr_pbmn"))
                change_pct = _safe_float(item.get("rate") or item.get("chgr") or item.get("prdy_ctrt"))
                sym = (item.get("symb") or item.get("stck_shrn_iscd") or "").strip()
                name = (item.get("name") or item.get("hts_kor_isnm") or sym).strip()
                result.append({
                    "rank": i + 1,
                    "symbol": sym,
                    "name": name,
                    "value": amount or 0.0,
                    "value_label": _fmt_usd(amount or 0.0),
                    "price": price,
                    "change_pct": change_pct,
                })
            return result
        except Exception as e:
            print(f"[KIS] overseas trading {path} exception: {e}")
    print(f"[KIS] overseas trading: 데이터 없음 (장 외 시간 또는 경로 미확인)")
    return []
