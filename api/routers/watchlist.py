from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase_db import SupabaseDB

router = APIRouter()


class WatchlistAddRequest(BaseModel):
    stock_code: str
    stock_name: str
    market_type: str  # "KR" | "US"


@router.get("/watchlist")
def fetch_watchlist():
    if not SupabaseDB.is_connected():
        return []
    items = SupabaseDB.fetch_watchlist()
    return [
        {
            "symbol": i["stock_code"],
            "name": i["stock_name"],
            "market_type": i["market_type"],
        }
        for i in items
    ]


@router.post("/watchlist")
def add_watchlist(body: WatchlistAddRequest):
    if not SupabaseDB.is_connected():
        raise HTTPException(status_code=503, detail="DB 미연결")
    result = SupabaseDB.insert_watchlist(
        body.stock_code, body.stock_name, body.market_type
    )
    if result is None:
        raise HTTPException(status_code=409, detail="이미 추가된 종목이거나 오류 발생")
    return {"ok": True}


@router.delete("/watchlist/{symbol}")
def remove_watchlist(symbol: str):
    if not SupabaseDB.is_connected():
        raise HTTPException(status_code=503, detail="DB 미연결")
    ok = SupabaseDB.delete_watchlist(symbol)
    if not ok:
        raise HTTPException(status_code=404, detail="종목 없음")
    return {"ok": True}
