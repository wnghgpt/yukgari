import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv

# .env 파일 로드
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

@st.cache_data(ttl=3600)
def _cached_kis_token(base_url, app_key, app_secret):
    url = f"{base_url}/oauth2/tokenP"
    headers = {"Content-Type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=5)
        if resp.status_code == 200:
            return resp.json().get("access_token")
        else:
            print(f"Token fetch failed: {resp.text}")
    except Exception as e:
        print(f"Token fetch error: {e}")
    return None

@st.cache_data(ttl=86400)
def _cached_kis_approval_key(base_url, app_key, app_secret):
    url = f"{base_url}/oauth2/Approval"
    headers = {"Content-Type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "secretkey": app_secret
    }
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=5)
        if resp.status_code == 200:
            return resp.json().get("approval_key")
        else:
            print(f"Approval Key fetch failed: {resp.text}")
    except Exception as e:
        print(f"Approval Key fetch error: {e}")
    return None

class KISClient:
    def __init__(self, acc_idx=4):
        # [계좌 1~4] 선택 가능
        self.app_key = os.getenv(f"KIS_ACC{acc_idx}_KEY")
        self.app_secret = os.getenv(f"KIS_ACC{acc_idx}_SECRET")
        self.acc_no = os.getenv(f"KIS_ACC{acc_idx}_NO")
        
        if not self.app_key or not self.app_secret:
            # Fallback to ACC4 if the index fails
            self.app_key = os.getenv("KIS_ACC4_KEY")
            self.app_secret = os.getenv("KIS_ACC4_SECRET")
            self.acc_no = os.getenv("KIS_ACC4_NO", "46903020-01")

        # 계좌번호 앞 8자리 / 뒤 2자리 분리
        acc_clean = self.acc_no.replace("-", "").strip()
        self.cano = acc_clean[:8]
        self.acnt_prdt_cd = acc_clean[8:10] if len(acc_clean) >= 10 else "01"
        
        is_virtual = os.getenv("KIS_VIRTUAL", "False").lower() == "true"
        if is_virtual:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
            self.tr_id_balance = "VTTC8434R"
        else:
            self.base_url = "https://openapi.koreainvestment.com:9443"
            self.tr_id_balance = "TTTC8434R"
            
    def get_approval_key(self):
        """웹소켓용 실시간 접속키 발급 (24시간 캐시)"""
        return _cached_kis_approval_key(self.base_url, self.app_key, self.app_secret)

    def get_access_token(self):
        """액세스 토큰 발급/갱신 (1시간 캐시)"""
        return _cached_kis_token(self.base_url, self.app_key, self.app_secret)

    def fetch_balance(self):
        """계좌 잔고 및 보유 종목 조회"""
        token = self.get_access_token()
        if not token:
            return None
            
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": self.tr_id_balance
        }
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=5)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"Balance fetch failed: {resp.text}")
        except Exception as e:
            print(f"Balance fetch error: {e}")
        return None

    def post_order_cash(self, code, qty, price, is_buy=True, is_market=False):
        """현금주식 주문 전송 (매수/매도)
        Args:
            code (str): 종목코드 (6자리)
            qty (int): 주문수량
            price (int): 주문단가 (시장가일 경우 0)
            is_buy (bool): True=매수, False=매도
            is_market (bool): True=시장가(01), False=지정가(00)
        """
        token = self.get_access_token()
        if not token:
            return {"rt_cd": "9", "msg1": "인증 토큰 획득 실패"}
            
        is_vts = os.getenv("KIS_VIRTUAL", "False").lower() == "true"
        
        if is_buy:
            tr_id = "VTTC0802U" if is_vts else "TTTC0802U"
        else:
            tr_id = "VTTC0801U" if is_vts else "TTTC0801U"
            
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": tr_id
        }
        
        # 시간대 체크 및 자동 분기
        from datetime import datetime
        now_time = datetime.now().time()
        is_regular_time = (now_time >= datetime.strptime("09:00:00", "%H:%M:%S").time()) and \
                           (now_time <= datetime.strptime("15:30:00", "%H:%M:%S").time())
        
        # 만약 야간(NXT 시간대)인 경우 SOR 최선집행 또는 대체거래소 코드로 자동 전환을 유도
        # (기본 API는 최선집행 파라미터를 유연하게 받으므로, 오류 차단을 위해 경고 혹은 대체 파라미터를 탑재할 수 있습니다.)
        ord_dvsn_code = "01" if is_market else "00"
        
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": code,
            "ORD_DVSN": ord_dvsn_code,
            "ORD_QTY": str(qty),
            "ORD_UNPR": "0" if is_market else str(price)
        }
        
        try:
            resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=5)
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"rt_cd": str(resp.status_code), "msg1": f"API 오류: {resp.text}"}
        except Exception as e:
            return {"rt_cd": "9", "msg1": f"연결 실패: {str(e)}"}

