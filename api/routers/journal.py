from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from supabase_db import SupabaseDB

router = APIRouter()


class JournalCreateRequest(BaseModel):
    ticker: str
    pattern: str
    date: str
    stages: int
    channel_top: Optional[float] = None
    channel_bottom: Optional[float] = None
    entry1_price: Optional[float] = None
    entry1_weight: Optional[float] = None
    entry2_price: Optional[float] = None
    entry2_weight: Optional[float] = None
    entry3_price: Optional[float] = None
    entry3_weight: Optional[float] = None
    entry4_price: Optional[float] = None
    entry4_weight: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    result: str = "감시"
    memo: Optional[str] = None


@router.get("/journal")
def fetch_journal():
    return SupabaseDB.fetch_trades()


@router.post("/journal")
async def create_journal(body: JournalCreateRequest):
    data, err = await asyncio.to_thread(SupabaseDB.insert_trade, body.model_dump())
    if err:
        raise HTTPException(status_code=500, detail=err)
    # 감시/보유 상태면 알림 등록 + KIS 구독
    if body.result in ("감시", "보유") and data:
        try:
            from api.services import alert_monitor
            from api.ws.price import backend_subscribe
            trade = data[0] if isinstance(data, list) else data
            alert_monitor.register_alert(trade)
            asyncio.create_task(backend_subscribe(body.ticker))
            if body.result == "감시":
                from api.services.telegram import format_watch_alert, send_message
                asyncio.create_task(send_message(format_watch_alert(trade)))
        except Exception as e:
            print(f"[Alert] 등록 오류: {e}")
    return data


@router.patch("/journal/{trade_id}")
async def update_journal(trade_id: str, request: Request):
    payload = await request.json()
    ok = await asyncio.to_thread(SupabaseDB.update_trade, trade_id, payload)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    # result 변경 시 알림 재등록 또는 해제
    try:
        from api.services import alert_monitor
        from api.ws.price import backend_subscribe
        if "result" in payload:
            if payload["result"] in ("감시", "보유"):
                # 최신 데이터로 재등록
                from supabase_db import SupabaseDB
                trades = await asyncio.to_thread(SupabaseDB.fetch_trades)
                trade = next((t for t in trades if str(t.get("id")) == str(trade_id)), None)
                if trade:
                    alert_monitor.register_alert(trade)
                    asyncio.create_task(backend_subscribe(trade["ticker"]))
            else:
                alert_monitor.unregister_alert(trade_id)
    except Exception as e:
        print(f"[Alert] PATCH 알림 처리 오류: {e}")
    return {"ok": True}


@router.delete("/journal/{trade_id}")
def delete_journal(trade_id: str):
    ok = SupabaseDB.delete_trade(trade_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}
