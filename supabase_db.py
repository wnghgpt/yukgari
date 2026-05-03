import os
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

    @staticmethod
    def insert_watchlist(stock_code, stock_name, market_type):
        """관심 종목 추가"""
        if not SupabaseDB.is_connected():
            return None
        
        payload = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "market_type": market_type
        }
        try:
            response = supabase.table("watchlist").insert(payload).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            # 중복 추가 시 에러 발생 가능하므로 예외 처리
            print(f"DB Insert Watchlist Error: {e}")
            return None

    @staticmethod
    def fetch_watchlist():
        """관심 종목 전체 조회"""
        if not SupabaseDB.is_connected():
            return []
        try:
            response = supabase.table("watchlist").select("*").order("created_at", desc=False).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"DB Fetch Watchlist Error: {e}")
            return []

    @staticmethod
    def delete_watchlist(stock_code):
        """관심 종목 삭제"""
        if not SupabaseDB.is_connected():
            return False
        try:
            response = supabase.table("watchlist").delete().eq("stock_code", stock_code).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"DB Delete Watchlist Error: {e}")
            return False
