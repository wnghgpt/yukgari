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
    yield


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
