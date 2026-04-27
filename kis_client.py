import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

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
