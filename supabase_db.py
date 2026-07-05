import os
import math
import numpy as np
from datetime import date, datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 싱글톤 클라이언트 객체 생성
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY and "your_supabase_" not in SUPABASE_URL:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Supabase Client Init Error: {e}")


class SupabaseDB:
    @staticmethod
    def is_connected():
        return supabase is not None

    # --- [1] 감시 주문 (watch_orders) CRUD ---
    
    @staticmethod
    def insert_watch_order(stock_code, stock_name, order_type, strat_name, target_price, qty):
        """감시 주문 등록"""
        if not SupabaseDB.is_connected():
            return None
        
        payload = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "order_type": order_type,
            "strat_name": strat_name,
            "target_price": float(target_price),
            "qty": str(qty),
            "status": "🟡 감시 중"
        }
        try:
            response = supabase.table("watch_orders").insert(payload).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            print(f"DB Insert Watch Order Error: {e}")
        return None

    @staticmethod
    def fetch_watch_orders():
        """감시 주문 전체 조회"""
        if not SupabaseDB.is_connected():
            return []
        
        try:
            response = supabase.table("watch_orders").select("*").order("created_at", desc=False).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"DB Fetch Watch Orders Error: {e}")
            return []

    @staticmethod
    def update_watch_order_status(order_id, status):
        """감시 주문 상태 업데이트 (예: 타점 도달, 체결 완료 등)"""
        if not SupabaseDB.is_connected():
            return False
        
        try:
            response = supabase.table("watch_orders").update({"status": status}).eq("id", order_id).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"DB Update Watch Order Status Error: {e}")
            return False

    @staticmethod
    def delete_watch_order(order_id):
        """감시 주문 삭제 (취소 시)"""
        if not SupabaseDB.is_connected():
            return False
        
        try:
            response = supabase.table("watch_orders").delete().eq("id", order_id).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"DB Delete Watch Order Error: {e}")
            return False

    # --- [2] 체결 내역 (trade_history) CRUD ---
    
    @staticmethod
    def insert_trade_history(stock_name, buy_price, sell_price, profit_pct):
        """체결 내역/매매 일지 기록"""
        if not SupabaseDB.is_connected():
            return None
        
        payload = {
            "stock_name": stock_name,
            "buy_price": float(buy_price),
            "sell_price": float(sell_price),
            "profit_pct": float(profit_pct)
        }
        try:
            response = supabase.table("trade_history").insert(payload).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            print(f"DB Insert Trade History Error: {e}")
        return None

    @staticmethod
    def fetch_trade_history():
        """체결 내역 조회"""
        if not SupabaseDB.is_connected():
            return []
        
        try:
            response = supabase.table("trade_history").select("*").order("trade_date", desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"DB Fetch Trade History Error: {e}")
            return []

    # --- [3] 관심 종목 (watchlist) CRUD ---

    # --- [3-u] 유저 ---

    @staticmethod
    def fetch_user(user_id: str):
        if not SupabaseDB.is_connected():
            return None
        try:
            r = supabase.table("users").select("*").eq("id", user_id).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            print(f"DB Fetch User Error: {e}")
            return None

    @staticmethod
    def update_user_chat_id(user_id: str, chat_id: int) -> bool:
        if not SupabaseDB.is_connected():
            return False
        try:
            r = supabase.table("users").update({"telegram_chat_id": chat_id}).eq("id", user_id).execute()
            return len(r.data) > 0
        except Exception as e:
            print(f"DB Update User ChatId Error: {e}")
            return False

    @staticmethod
    def fetch_users_with_telegram() -> list:
        if not SupabaseDB.is_connected():
            return []
        try:
            r = supabase.table("users").select("*").not_.is_("telegram_chat_id", "null").execute()
            return r.data or []
        except Exception as e:
            print(f"DB Fetch Users Telegram Error: {e}")
            return []

    @staticmethod
    def fetch_all_users() -> list:
        if not SupabaseDB.is_connected():
            return []
        try:
            r = supabase.table("users").select("id").execute()
            return r.data or []
        except Exception as e:
            print(f"DB Fetch All Users Error: {e}")
            return []

    @staticmethod
    def insert_watchlist(stock_code, stock_name, market_type, user_id: str):
        """관심 종목 추가"""
        if not SupabaseDB.is_connected():
            return None
        try:
            max_resp = supabase.table("watchlist").select("sort_order").eq("user_id", user_id).order("sort_order", desc=True).limit(1).execute()
            next_order = (max_resp.data[0]["sort_order"] or 0) + 1 if max_resp.data else 1
            payload = {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "market_type": market_type,
                "user_id": user_id,
                "sort_order": next_order,
            }
            response = supabase.table("watchlist").insert(payload).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"DB Insert Watchlist Error: {e}")
            return None

    @staticmethod
    def fetch_watchlist(user_id: str) -> list:
        """관심 종목 조회 (유저별)"""
        if not SupabaseDB.is_connected():
            return []
        try:
            response = supabase.table("watchlist").select("*").eq("user_id", user_id).order("sort_order", desc=False).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"DB Fetch Watchlist Error: {e}")
            return []

    @staticmethod
    def reorder_watchlist(user_id: str, items: list) -> bool:
        """관심 종목 순서 변경: items = [{"stock_code": ..., "sort_order": ...}, ...]"""
        if not SupabaseDB.is_connected():
            return False
        try:
            for item in items:
                supabase.table("watchlist").update({"sort_order": item["sort_order"]}).eq("stock_code", item["stock_code"]).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            print(f"DB Reorder Watchlist Error: {e}")
            return False

    @staticmethod
    def delete_watchlist(stock_code: str, user_id: str) -> bool:
        """관심 종목 삭제"""
        if not SupabaseDB.is_connected():
            return False
        try:
            response = supabase.table("watchlist").delete().eq("stock_code", stock_code).eq("user_id", user_id).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"DB Delete Watchlist Error: {e}")
            return False

    # --- [4] 매매 일지 (trades) CRUD ---

    @staticmethod
    def fetch_trades(user_id: str = None):
        if not SupabaseDB.is_connected():
            return []
        try:
            q = supabase.table("trades").select("*").order("date", desc=True)
            if user_id:
                q = q.eq("user_id", user_id)
            response = q.execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"DB Fetch Trades Error: {e}")
            return []

    @staticmethod
    def _sanitize(payload: dict) -> dict:
        import pandas as pd
        result = {}
        for k, v in payload.items():
            if v is None or v == "":
                result[k] = None
                continue
            # pd.NaT / pd.NA 먼저 처리 (isinstance datetime 체크보다 앞에)
            try:
                if pd.isna(v):
                    result[k] = None
                    continue
            except (TypeError, ValueError):
                pass
            if isinstance(v, bool):
                result[k] = v
            elif isinstance(v, np.bool_):
                result[k] = bool(v)
            elif isinstance(v, np.integer):
                result[k] = int(v)
            elif isinstance(v, np.floating):
                f = float(v)
                if math.isnan(f):
                    result[k] = None
                elif f == int(f):
                    result[k] = int(f)
                else:
                    result[k] = f
            elif isinstance(v, float):
                if math.isnan(v):
                    result[k] = None
                elif v == int(v):
                    result[k] = int(v)
                else:
                    result[k] = v
            elif isinstance(v, datetime):
                result[k] = v.isoformat()
            elif isinstance(v, date):
                result[k] = v.isoformat()
            else:
                result[k] = v
        return result

    @staticmethod
    def insert_trade(payload: dict):
        if not SupabaseDB.is_connected():
            return None, "Supabase 미연결"
        try:
            sanitized = SupabaseDB._sanitize(payload)
            clean = {k: v for k, v in sanitized.items() if v is not None and k != "id" and k != "created_at"}
            response = supabase.table("trades").insert(clean).execute()
            if response.data:
                return response.data[0], None
            return None, "응답 데이터 없음"
        except Exception as e:
            print(f"DB Insert Trade Error: {e}")
            return None, str(e)

    @staticmethod
    def update_trade(trade_id: str, payload: dict):
        if not SupabaseDB.is_connected():
            return False
        try:
            sanitized = SupabaseDB._sanitize(payload)
            clean = {k: v for k, v in sanitized.items() if k not in ("id", "created_at")}
            print(f"[UPDATE] trade_id={trade_id[:8]} payload={clean}")
            response = supabase.table("trades").update(clean).eq("id", trade_id).execute()
            print(f"[UPDATE] response.data={response.data}")
            return len(response.data) > 0
        except Exception as e:
            print(f"[UPDATE] Exception: {e}")
            return False

    @staticmethod
    def delete_trade(trade_id: str, user_id: str = None):
        if not SupabaseDB.is_connected():
            return False
        try:
            q = supabase.table("trades").delete().eq("id", trade_id)
            if user_id:
                q = q.eq("user_id", user_id)
            response = q.execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"DB Delete Trade Error: {e}")
            return False
