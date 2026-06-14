"""
trades 테이블에서 한글 이름으로 저장된 ticker를 종목코드로 변환.
실행: python scripts/migrate_ticker_to_code.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from supabase_db import SupabaseDB, supabase
from data_loader import StockDataLoader


def resolve_to_code(ticker: str):
    if not any('가' <= c <= '힣' for c in ticker):
        return None  # 이미 코드
    try:
        results = StockDataLoader.search_stock_naver(ticker)
        if results:
            code = results[0].get('symbol', '')
            if code and code.isdigit():
                return code
    except Exception as e:
        print(f"  검색 실패: {e}")
    return None


def main():
    trades = SupabaseDB.fetch_trades()
    korean = [t for t in trades if any('가' <= c <= '힣' for c in t.get('ticker', ''))]
    print(f"한글 ticker 항목: {len(korean)}개\n")

    for t in korean:
        old_ticker = t['ticker']
        new_code = resolve_to_code(old_ticker)
        if not new_code:
            print(f"[SKIP] {old_ticker} → 코드 못 찾음")
            continue
        print(f"[UPDATE] {old_ticker} → {new_code}  (id={str(t['id'])[:8]}...)")
        ok = SupabaseDB.update_trade(str(t['id']), {'ticker': new_code})
        if not ok:
            print(f"  실패!")

    print("\n완료.")


if __name__ == '__main__':
    main()
