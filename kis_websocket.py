import asyncio
import websockets
import json
import os
from dotenv import load_dotenv
from kis_client import KISClient

load_dotenv()

class KISWebSocket:
    def __init__(self, acc_idx=4):
        self.client = KISClient(acc_idx=acc_idx)
        is_virtual = os.getenv("KIS_VIRTUAL", "False").lower() == "true"
        if is_virtual:
            self.ws_url = "ws://ops.koreainvestment.com:31000"
        else:
            self.ws_url = "ws://ops.koreainvestment.com:21000"
            
        self.approval_key = None
        self.websocket = None
        self.is_running = False
        
    async def connect(self):
        """웹소켓 서버 연결"""
        self.approval_key = self.client.get_approval_key()
        if not self.approval_key:
            print("Approval Key 발급 실패. 연결 불가.")
            return False
            
        try:
            self.websocket = await websockets.connect(self.ws_url, ping_interval=30, ping_timeout=10)
            self.is_running = True
            print(f"WebSocket Connected: {self.ws_url}")
            return True
        except Exception as e:
            print(f"WebSocket Connection Error: {e}")
            return False
            
    async def subscribe(self, symbol: str):
        """특정 종목 실시간 체결가 구독 요청"""
        if not self.websocket or not self.is_running:
            print("웹소켓이 연결되어 있지 않습니다.")
            return False

        payload = {
            "header": {
                "approval_key": self.approval_key,
                "custtype": "P",
                "tr_type": "1",
                "content-type": "utf-8"
            },
            "body": {
                "input": {
                    "tr_id": "H0UNCNT0",
                    "tr_key": symbol
                }
            }
        }
        try:
            await self.websocket.send(json.dumps(payload))
            print(f"Subscribed to {symbol}")
            return True
        except Exception as e:
            print(f"Subscribe Error for {symbol}: {e}")
            return False

    async def subscribe_fills(self, account_no: str):
        """체결 통보 구독 (H0STCNI0) — TR_KEY = 계좌번호 앞 8자리"""
        if not self.websocket or not self.is_running:
            return False
        cano = account_no.split("-")[0]
        payload = {
            "header": {
                "approval_key": self.approval_key,
                "custtype": "P",
                "tr_type": "1",
                "content-type": "utf-8"
            },
            "body": {
                "input": {
                    "tr_id": "H0STCNI0",
                    "tr_key": cano
                }
            }
        }
        try:
            await self.websocket.send(json.dumps(payload))
            print(f"[KIS] 체결통보 구독: 계좌 {cano}")
            return True
        except Exception as e:
            print(f"[KIS] 체결통보 구독 오류: {e}")
            return False

    async def receive_loop(self, callback=None, fill_callback=None):
        """실시간 데이터 수신 무한 루프"""
        while self.is_running:
            try:
                message = await self.websocket.recv()

                # JSON 형식의 등록 응답
                if message.startswith("{"):
                    data = json.loads(message)
                    print(f"Response received: {data.get('body', {}).get('msg1')}")
                    continue

                parts = message.split("|")
                if len(parts) < 4:
                    continue

                tr_id = parts[1]
                data_fields = parts[3].split("^")

                # 실시간 시세 (H0STCNT0 / H0UNCNT0)
                if tr_id in ("H0STCNT0", "H0UNCNT0"):
                    if len(data_fields) >= 3:
                        code = data_fields[0]
                        price = int(data_fields[2])
                        if callback:
                            await callback(code, price)

                # 체결 통보 (H0STCNI0)
                elif tr_id == "H0STCNI0":
                    if len(data_fields) >= 12:
                        # field index: 4=매수매도구분(1매도/2매수), 8=종목코드, 9=체결수량, 10=체결단가
                        sll_buy = data_fields[4].strip()   # "1"=매도 "2"=매수
                        ticker  = data_fields[8].strip()
                        qty     = int(data_fields[9] or 0)
                        price   = float(data_fields[10] or 0)
                        if fill_callback and ticker and qty > 0 and price > 0:
                            await fill_callback(ticker, qty, price, sll_buy)
                        else:
                            print(f"[체결통보] {ticker} {'매수' if sll_buy=='2' else '매도'} {qty}주 @ {price}")
                            
            except websockets.ConnectionClosed:
                print("WebSocket Connection Closed. Reconnecting...")
                self.is_running = False
                # 5초 대기 후 자동 재연동 시도
                await asyncio.sleep(5)
                await self.connect()
            except Exception as e:
                print(f"Receive Loop Error: {e}")
                await asyncio.sleep(1)
                
    async def close(self):
        """웹소켓 종료"""
        self.is_running = False
        if self.websocket:
            await self.websocket.close()
            print("WebSocket Closed.")
