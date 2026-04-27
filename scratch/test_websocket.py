import asyncio
import sys
import os

# 부모 디렉토리 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv('/Users/juho/stocks/.env')

from kis_websocket import KISWebSocket

async def main():
    ws = KISWebSocket(acc_idx=4)
    
    print("1. 한투 웹소켓 연결 중...")
    connected = await ws.connect()
    if not connected:
        print("연결 실패!")
        return
        
    print("2. 삼성중공업(010140) 구독 요청...")
    await ws.subscribe("010140")
    
    print("3. 데이터 수신 대기 (10초간 실행 후 자동 종료)...")
    try:
        # 10초 후에 종료되는 타스크 생성
        await asyncio.wait_for(ws.receive_loop(), timeout=10.0)
    except asyncio.TimeoutError:
        print("\n10초 경과로 테스트 종료.")
    finally:
        await ws.close()

if __name__ == "__main__":
    asyncio.run(main())
