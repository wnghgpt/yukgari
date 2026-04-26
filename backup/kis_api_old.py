from config import KIS_APP_KEY, KIS_APP_SECRET, KIS_VIRTUAL, KIS_ACCOUNT_NO
from pykis import Api
from pykis.public_api import DomainInfo
import pandas as pd
from typing import Optional

class KISClient:
    def __init__(self):
        try:
            key_info = {
                "appkey": KIS_APP_KEY,
                "appsecret": KIS_APP_SECRET
            }
            domain_info = DomainInfo(kind="virtual" if KIS_VIRTUAL else "real")
            
            # API 인스턴스 생성
            self.kis = Api(key_info=key_info, domain_info=domain_info)
            
            # 내 계좌(Account) 인식 연동
            # "12345678-01" 형식을 "12345678", "01" 로 안전하게 파싱
            acc_str = KIS_ACCOUNT_NO.replace("-", "").strip()
            if len(acc_str) >= 10:
                self.kis.set_account({"account_code": acc_str[:8], "product_code": acc_str[8:10]})
                
        except Exception as e:
            print(f"PyKIS Init Error: {e}")
            self.kis = None

    def get_current_price(self, symbol: str) -> Optional[int]:
        if not self.kis: return None
        try:
            price = self.kis.get_kr_current_price(symbol)
            return int(price)
        except Exception as e:
            print(f"Price fetching Error: {e}")
        return None

    def get_buyable_cash(self) -> int:
        """가용 예수금(주식 매수 가능 현금) 조회"""
        if not self.kis or not self.kis.account:
            return 10000000 # 백업용 가상 통신실패 예수금
        try:
            cash = self.kis.get_kr_buyable_cash()
            return int(cash)
        except Exception as e:
            print(f"Buyable Cash Fetch Error: {e}")
            return 10000000
            
    def get_my_stocks(self) -> pd.DataFrame:
        """현재 내 계좌의 보유 종목 테이블 조회"""
        fallback_df = pd.DataFrame({
            "종목명": ["삼성전자(모의)", "카카오(모의)"], 
            "보유수량": [10, 5], 
            "매입단가": [70000, 45000],
            "수익율": [2.5, -1.2],
            "현재가": [71750, 44460]
        })
        
        if not self.kis or not self.kis.account:
            return fallback_df
        try:
            df = self.kis.get_kr_stock_balance()
            if df is None or df.empty: # 보유 종목이 아예 없는 경우
                return pd.DataFrame(columns=["종목명", "보유수량", "매입단가", "수익율", "현재가"])
            return df
        except Exception as e:
            print(f"My Stocks Fetch Error: {e}")
            return fallback_df

    def get_ohlcv(self, symbol: str, period: str = 'D') -> Optional[pd.DataFrame]:
        """
        API를 통해 캔들 데이터를 불러옵니다. period: 'D'(일), 'W'(주)
        """
        if not self.kis: 
            return self._generate_mock_candles() # 로컬 UI 테스트용 (통신실패시)
        
        try:
            # 자체 통신 100봉 함수 사용 (period 변수 전달)
            df = self._get_100days_ohlcv(symbol, period)
            
            if df is not None and not df.empty:
                return df
            return self._generate_mock_candles(self.get_current_price(symbol) or 70000)
                
        except Exception as e:
            print(f"OHLCV Fetch Error: {e}")
            return self._generate_mock_candles(self.get_current_price(symbol) or 70000)

    def _get_100days_ohlcv(self, symbol: str, period: str = 'D') -> Optional[pd.DataFrame]:
        """트래픽 제한 없이 1번의 호출로 100봉 데이터를 가져오는 KIS HTTP 우회 통신"""
        import requests
        from datetime import datetime, timedelta
        
        if not self.kis: return None
        try:
            url = f"{self.kis.domain.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
            headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": self.kis.token.value if self.kis.token and self.kis.token.value else "",
                "appkey": self.kis.key['appkey'],
                "appsecret": self.kis.key['appsecret'],
                "tr_id": "FHKST03010100", # 국내주식업종기간별시세 조회 API
                "custtype": "P",
            }
            
            today = datetime.now()
            # 일봉 100개면 달력상 200일, 주봉 100개면 달력상 750일 전
            delta_days = 200 if period == 'D' else 750
            start = today - timedelta(days=delta_days)
            
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": start.strftime('%Y%m%d'),
                "FID_INPUT_DATE_2": today.strftime('%Y%m%d'),
                "FID_PERIOD_DIV_CODE": period,
                "FID_ORG_ADJ_PRC": "0" # 수정주가 반영
            }
            
            resp = requests.get(url, headers=headers, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('rt_cd') == '0' and 'output2' in data:
                    res_df = pd.DataFrame(data['output2'])
                    if not res_df.empty:
                        res_df['Date'] = pd.to_datetime(res_df['stck_bsop_date'])
                        for col, new_col in zip(['stck_oprc', 'stck_hgpr', 'stck_lwpr', 'stck_clpr', 'acml_vol'], 
                                                ['Open', 'High', 'Low', 'Close', 'Volume']):
                            res_df[new_col] = pd.to_numeric(res_df[col])
                        return res_df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception as e:
            print(f"100Days Fetch Error: {e}")
        return None

    def _generate_mock_candles(self, base: float = 70000) -> pd.DataFrame:
        """Dashboard 차트 UI 제작을 위한 가상 주가 데이터"""
        import numpy as np
        dates = pd.date_range(end=pd.Timestamp.today(), periods=100)
        # base 변동폭을 주가 비율에 맞게 조정 (예: 18만 원일 땐 더 크게)
        vol = base * 0.015
        closes = base + np.cumsum(np.random.randn(100) * vol)
        highs = closes + np.abs(np.random.randn(100) * (vol * 1.5))
        lows = closes - np.abs(np.random.randn(100) * (vol * 1.5))
        opens = closes - np.random.randn(100) * (vol * 0.5)
        
        return pd.DataFrame({
            "Date": dates,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": np.random.randint(10000, 100000, 100)
        })
