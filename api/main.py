import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers.stock import router as stock_router
from api.routers.watchlist import router as watchlist_router
from api.routers.journal import router as journal_router
from api.ws.price import router as ws_router


async def _daily_summary_loop():
    """매일 KST 08:00, 14:00 에 감시 요약 텔레그램 전송"""
    from datetime import datetime, timezone, timedelta
    KST = timezone(timedelta(hours=9))
    TARGET_HOURS = (8, 14)
    while True:
        now = datetime.now(KST)
        next_fires = []
        for h in TARGET_HOURS:
            t = now.replace(hour=h, minute=0, second=0, microsecond=0)
            if t <= now:
                t += timedelta(days=1)
            next_fires.append(t)
        wait = (min(next_fires) - now).total_seconds()
        await asyncio.sleep(wait)
        try:
            from api.services.telegram import send_daily_summary
            await send_daily_summary()
        except Exception as e:
            print(f"[Telegram] 정기 요약 오류: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 기존 감시 종목 로드 + KIS WebSocket 구독
    try:
        from supabase_db import SupabaseDB
        from api.services import alert_monitor
        from api.ws.price import backend_subscribe
        trades = await asyncio.to_thread(SupabaseDB.fetch_trades)
        alert_monitor.load_from_trades(trades)
        from api.services.alert_monitor import WATCH_RESULTS
        symbols = {t["ticker"] for t in trades if t.get("result") in WATCH_RESULTS}
        for sym in symbols:
            asyncio.create_task(backend_subscribe(sym))
    except Exception as e:
        print(f"[Alert] 시작 로드 오류: {e}")
    asyncio.create_task(_daily_summary_loop())
    asyncio.create_task(_prewarm_ranking_cache())
    from api.services.telegram_bot import poll_loop as _bot_poll
    asyncio.create_task(_bot_poll())
    from api.services.kis_sync import daily_sync_loop as _sync_loop
    asyncio.create_task(_sync_loop())
    yield


async def _prewarm_ranking_cache():
    """서버 시작 직후 랭킹 캐시 미리 채움 — 첫 요청 즉시 응답"""
    await asyncio.sleep(2)  # lifespan 안정화 대기
    from api.routers.stock import _cached_rank
    from api.services.krx import fetch_domestic_marcap
    from api.services.kis import (
        fetch_domestic_trading,
        fetch_overseas_marcap, fetch_overseas_trading,
    )
    tasks = [
        ("dom_marcap",  fetch_domestic_marcap),
        ("dom_trading", fetch_domestic_trading),
        ("us_marcap",   fetch_overseas_marcap),
        ("us_trading",  fetch_overseas_trading),
    ]
    for key, fn in tasks:
        try:
            await asyncio.to_thread(_cached_rank, key, fn)
        except Exception as e:
            print(f"[Prewarm] {key} 오류: {e}")


app = FastAPI(title="Stocks API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stock_router, prefix="/api")
app.include_router(watchlist_router, prefix="/api")
app.include_router(journal_router, prefix="/api")
app.include_router(ws_router)


@app.get("/")
def root():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
