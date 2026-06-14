import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# symbol -> set of WebSocket clients
_subscriptions: dict[str, set[WebSocket]] = {}
_kis_ws = None
_kis_lock = asyncio.Lock()
_backend_symbols: set[str] = set()   # 프론트 없이 백엔드가 직접 구독하는 심볼


async def backend_subscribe(symbol: str):
    """프론트엔드 없이 백엔드 감시용으로 KIS WebSocket 구독"""
    _backend_symbols.add(symbol)
    kis = await _get_kis_ws()
    if kis:
        await kis.subscribe(symbol)
        print(f"[Alert] KIS 백엔드 구독: {symbol}")


async def subscribe_fill_notifications():
    """체결 통보 구독 (H0STCNI0) — 서버 시작 시 1회 호출"""
    from config import KIS_SESSIONS
    if not KIS_SESSIONS:
        return
    kis = await _get_kis_ws()
    if kis:
        await kis.subscribe_fills(KIS_SESSIONS[0]["acc_no"])


async def _fill_callback(ticker: str, qty: int, price: float, sll_buy: str):
    """체결 통보 수신 → 일지 즉시 업데이트"""
    try:
        from api.services.kis_sync import apply_fill_to_journal
        await apply_fill_to_journal(ticker, qty, price, sll_buy)
    except Exception as e:
        print(f"[Fill] 일지 업데이트 오류: {e}")


async def _get_kis_ws():
    global _kis_ws
    async with _kis_lock:
        if _kis_ws is None or not _kis_ws.is_running:
            try:
                from kis_websocket import KISWebSocket
                _kis_ws = KISWebSocket()
                connected = await _kis_ws.connect()
                if connected:
                    asyncio.create_task(_receive_loop())
            except Exception as e:
                print(f"KIS WebSocket init error: {e}")
                _kis_ws = None
    return _kis_ws


async def _broadcast(symbol: str, price: int):
    clients = _subscriptions.get(symbol, set()).copy()
    dead = set()
    for ws in clients:
        try:
            await ws.send_json({"symbol": symbol, "price": price})
        except Exception:
            dead.add(ws)
    for ws in dead:
        _subscriptions.get(symbol, set()).discard(ws)

    # 감시 알림 체크
    try:
        from api.services import alert_monitor
        asyncio.create_task(alert_monitor.on_price(symbol, float(price)))
    except Exception:
        pass


async def _receive_loop():
    global _kis_ws
    if _kis_ws:
        await _kis_ws.receive_loop(callback=_broadcast, fill_callback=_fill_callback)


@router.websocket("/ws/price")
async def price_ws(websocket: WebSocket):
    await websocket.accept()
    subscribed: set[str] = set()

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                continue

            action = data.get("action")  # "subscribe" | "unsubscribe"
            symbol = data.get("symbol", "").strip()
            if not symbol:
                continue

            if action == "subscribe":
                if symbol not in _subscriptions:
                    _subscriptions[symbol] = set()
                _subscriptions[symbol].add(websocket)
                subscribed.add(symbol)

                kis = await _get_kis_ws()
                if kis:
                    await kis.subscribe(symbol)

            elif action == "unsubscribe":
                _subscriptions.get(symbol, set()).discard(websocket)
                subscribed.discard(symbol)

    except WebSocketDisconnect:
        pass
    finally:
        for sym in subscribed:
            _subscriptions.get(sym, set()).discard(websocket)
