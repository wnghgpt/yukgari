import pandas as pd
import FinanceDataReader as fdr
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict

class StockDataLoader:
    _local_cache = None

    @staticmethod
    def update_local_cache():
        import os
        import json
        cache_file = os.path.join(os.path.dirname(__file__), 'stock_list.json')
        
        # 캐시 파일이 이미 있다면 로드
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    StockDataLoader._local_cache = json.load(f)
                    if StockDataLoader._local_cache:
                        return StockDataLoader._local_cache
            except Exception as e:
                print(f"Error loading stock cache: {e}")

        # 캐시 파일이 없으면 새로 생성
        try:
            url = 'https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
            df = pd.read_html(url, encoding='cp949')[0]
            df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
            
            mapping = {}
            for _, row in df.iterrows():
                mapping[str(row['회사명']).strip()] = str(row['종목코드']).strip()
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=4)
            
            StockDataLoader._local_cache = mapping
            return mapping
        except Exception as e:
            print(f"Failed to create local cache: {e}")
            # 최후의 수단: 주요 대형주라도 하드코딩
            fallback = {"삼성전자": "005930", "SK하이닉스": "000660", "LG에너지솔루션": "373220", "삼성바이오로직스": "207940", "현대차": "005380", "기아": "000270", "셀트리온": "068270", "POSCO홀딩스": "005490", "NAVER": "035420", "카카오": "035720", "네이버": "035420"}
            StockDataLoader._local_cache = fallback
            return fallback

    @staticmethod
    def get_stock_list():
        if StockDataLoader._local_cache is None:
            StockDataLoader.update_local_cache()
        return StockDataLoader._local_cache

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
    def search_stock_naver(query: str):
        import urllib.parse
        if not query:
            return []
        try:
            enc_query = urllib.parse.quote(query)
            url = f"https://ac.finance.naver.com/ac?q={enc_query}&q_enc=utf-8&st=111&r_format=json&r_enc=utf-8&r_unicode=0&t_koreng=1&type=pc"
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('items', [])
                results = []
                if items and len(items) > 0 and items[0]:
                    for item in items[0]:
                        name = item[0]
                        code = item[1]
                        results.append({"name": name, "symbol": code})
                return results
        except:
            pass
        return []

    @staticmethod
    def get_stock_info(symbol_or_name: str) -> Dict[str, str]:
        """
        FinanceDataReader(KRX) 및 네이버 자동완성을 활용하여 종목명과 코드를 매칭합니다.
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
        
        # 2. 이름인 경우 코드 찾기
        # 2-1. 로컬 오프라인 JSON 캐시 1순위 검색
        local_list = StockDataLoader.get_stock_list()
        if local_list:
            # 완전 일치 탐색
            if symbol_or_name in local_list:
                return {"name": symbol_or_name, "symbol": local_list[symbol_or_name]}
            
            # 부분 일치 탐색
            for k, v in local_list.items():
                if symbol_or_name in k:
                    return {"name": k, "symbol": v}

        # 2-2. 네이버 자동완성 API 백업
        naver_matches = StockDataLoader.search_stock_naver(symbol_or_name)
        if naver_matches:
            return naver_matches[0]

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
