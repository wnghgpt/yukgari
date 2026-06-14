"""
trades 테이블에서 name이 null인 항목의 종목명을 ticker로 검색해서 채움.
실행: python scripts/migrate_name.py
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from supabase_db import SupabaseDB
from data_loader import StockDataLoader


def fetch_name(ticker: str):
    try:
        results = StockDataLoader.search_stock_naver(ticker)
        if results:
            return results[0].get('name') or None
    except Exception as e:
        print(f"  검색 실패: {e}")
    return None


def main():
    trades = SupabaseDB.fetch_trades()
    no_name = [t for t in trades if not t.get('name')]
    print(f"name 없는 항목: {len(no_name)}개\n")

    for t in no_name:
        ticker = t['ticker']
        name = fetch_name(ticker)
        if not name:
            print(f"[SKIP] {ticker} → 이름 못 찾음")
            continue
        print(f"[UPDATE] {ticker} → {name}  (id={str(t['id'])[:8]}...)")
        SupabaseDB.update_trade(str(t['id']), {'name': name})
        time.sleep(0.2)

    print("\n완료.")


if __name__ == '__main__':
    main()
