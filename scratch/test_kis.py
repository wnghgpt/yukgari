import sys
import os

# 부모 디렉토리 경로를 추가하여 모듈을 불러옵니다.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kis_client import KISClient

kis = KISClient()
print(f"Target Account: {kis.acc_no} ({kis.cano}-{kis.acnt_prdt_cd})")
print(f"Target Domain: {kis.base_url}")

token = kis.get_access_token()
print(f"Token fetched: {token[:10] if token else 'Failed'}")

if token:
    balance_data = kis.fetch_balance()
    print("Balance Data Response:")
    import json
    print(json.dumps(balance_data, indent=2, ensure_ascii=False))
