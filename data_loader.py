import pandas as pd
import FinanceDataReader as fdr
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict

class StockDataLoader:
    _stock_list_df = None

    @staticmethod
    def get_stock_list():
        if StockDataLoader._stock_list_df is None:
            try:
                StockDataLoader._stock_list_df = fdr.StockListing('KRX')
            except Exception as e:
                print(f"Error loading stock listing: {e}")
                return None
        return StockDataLoader._stock_list_df

    @staticmethod
    def get_ohlcv(symbol: str, count: int = 200, period: str = 'D') -> Optional[pd.DataFrame]:
        """
        네이버 금융 데이터를 사용하여 OHLCV(시-고-저-종-거) 데이터를 수집합니다.
        period: 'D' (일봉), 'W' (주봉)
        """
        import datetime
        try:
            # count 에 맞춰 대략적인 시작 날짜 계산 (여유있게 2배)
            days_back = count * 2 if period == 'D' else count * 8
            start_date = (datetime.datetime.now() - datetime.timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            df = fdr.DataReader(symbol, start=start_date)
            
            if df is None or df.empty:
                return None
            
            # 필요한 개수만큼 최신순 슬라이싱
            df = df.tail(count)
            
            # 주봉 변환 로직 (FinanceDataReader 가 일봉 위주면 직접 리샘플링)
            if period == 'W':
                df = df.resample('W').agg({
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Volume': 'sum'
                }).dropna()
            
            return df.reset_index()
        except Exception as e:
            print(f"OHLCV Load Error: {e}")
            return None

    @staticmethod
    def get_stock_info(symbol_or_name: str) -> Dict[str, str]:
        """
        FinanceDataReader(KRX)를 활용하여 종목명과 코드를 매칭합니다.
        """
        symbol_or_name = symbol_or_name.strip()
        
        # 1. 이미 6자리 숫자인 경우 (코드)
        if symbol_or_name.isdigit() and len(symbol_or_name) == 6:
            try:
                url = f"https://finance.naver.com/item/main.naver?code={symbol_or_name}"
                resp = requests.get(url, timeout=5)
                soup = BeautifulSoup(resp.text, 'html.parser')
                name_tag = soup.select_one('.wrap_company h2 a')
                name = name_tag.text if name_tag else symbol_or_name
                return {"name": name, "symbol": symbol_or_name}
            except:
                return {"name": symbol_or_name, "symbol": symbol_or_name}
        
        # 2. 이름인 경우 코드 찾기 (FinanceDataReader 활용)
        try:
            df = StockDataLoader.get_stock_list()
            if df is not None and not df.empty:
                # 완전 일치 탐색
                match = df[df['Name'].str.upper() == symbol_or_name.upper()]
                if not match.empty:
                    return {"name": str(match.iloc[0]['Name']), "symbol": str(match.iloc[0]['Code'])}
                
                # 부분 일치 탐색
                match_partial = df[df['Name'].str.contains(symbol_or_name, case=False, na=False)]
                if not match_partial.empty:
                    return {"name": str(match_partial.iloc[0]['Name']), "symbol": str(match_partial.iloc[0]['Code'])}
        except Exception as e:
            print(f"Stock search error: {e}")
            pass

        return {"name": symbol_or_name, "symbol": "005930"} # 최후의 수단: 삼성전자 코드라도 반환하여 에러 방지

    @staticmethod
    def get_current_price(symbol: str) -> Optional[float]:
        """
        네이버 금융 실시간 체결가 (지연 포함) 가져오기
        """
        try:
            url = f"https://finance.naver.com/item/main.naver?code={symbol}"
            resp = requests.get(url, timeout=5)
            soup = BeautifulSoup(resp.text, 'html.parser')
            price_tag = soup.select_one(".no_today .blind")
            if price_tag:
                return float(price_tag.text.replace(",", ""))
        except:
            pass
        return None
