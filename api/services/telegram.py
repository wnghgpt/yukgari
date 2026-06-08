import asyncio
import requests
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


async def send_message(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] 설정 없음 — .env 에 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 입력 필요")
        return False

    def _post():
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        return resp.status_code == 200

    try:
        return await asyncio.to_thread(_post)
    except Exception as e:
        print(f"[Telegram] 전송 오류: {e}")
        return False
