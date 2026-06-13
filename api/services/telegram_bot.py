"""텔레그램 봇 폴링 — /register <code> 처리"""
import asyncio
import requests
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import TELEGRAM_BOT_TOKEN

_last_update_id = 0


def _get_updates(offset: int) -> list:
    if not TELEGRAM_BOT_TOKEN:
        return []
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
            params={"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
            timeout=35,
        )
        if r.status_code == 200:
            return r.json().get("result", [])
    except Exception as e:
        print(f"[Bot] getUpdates 오류: {e}")
    return []


def _send_reply(chat_id: int, text: str):
    if not TELEGRAM_BOT_TOKEN:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=5,
        )
    except Exception:
        pass


async def poll_loop():
    global _last_update_id
    print("[Bot] 텔레그램 봇 폴링 시작")
    while True:
        try:
            updates = await asyncio.to_thread(_get_updates, _last_update_id)
            for upd in updates:
                _last_update_id = upd["update_id"] + 1
                msg = upd.get("message", {})
                text = (msg.get("text") or "").strip()
                chat_id = msg.get("chat", {}).get("id")
                if not text or not chat_id:
                    continue

                if text.startswith("/register "):
                    code = text[len("/register "):].strip()
                    await _handle_register(chat_id, code)
                elif text == "/myid":
                    _send_reply(chat_id, f"내 chat_id: {chat_id}")
        except Exception as e:
            print(f"[Bot] 폴링 루프 오류: {e}")
            await asyncio.sleep(5)


async def _handle_register(chat_id: int, code: str):
    from supabase_db import SupabaseDB
    user = await asyncio.to_thread(SupabaseDB.fetch_user, code)
    if not user:
        _send_reply(chat_id, f"❌ 코드 '{code}' 를 찾을 수 없습니다.")
        return
    ok = await asyncio.to_thread(SupabaseDB.update_user_chat_id, code, chat_id)
    if ok:
        _send_reply(chat_id, f"✅ {user['nickname']}님 텔레그램 연결 완료!")
    else:
        _send_reply(chat_id, "❌ 연결 실패. 다시 시도해주세요.")
