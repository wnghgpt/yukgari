import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 한국투자증권 API 멀티 세션 설정 수집
KIS_SESSIONS = []

# 최대 10개까지의 슬롯을 검색하여 유효한 세션 정보 수집
for i in range(1, 11):
    key = os.getenv(f"KIS_ACC{i}_KEY", "")
    secret = os.getenv(f"KIS_ACC{i}_SECRET", "")
    acc_no = os.getenv(f"KIS_ACC{i}_NO", "")
    name = os.getenv(f"KIS_ACC{i}_NAME", f"계좌{i}")
    
    # 필수 정보(Key, Secret, No)가 모두 있는 경우에만 세션으로 인정
    if key and secret and acc_no and "입력" not in key:
        KIS_SESSIONS.append({
            "key": key,
            "secret": secret,
            "acc_no": acc_no,
            "name": name
        })

# 하위 호환성을 위한 기본값 (첫 번째 세션)
if KIS_SESSIONS:
    KIS_APP_KEY = KIS_SESSIONS[0]["key"]
    KIS_APP_SECRET = KIS_SESSIONS[0]["secret"]
    KIS_ACCOUNT_NO = KIS_SESSIONS[0]["acc_no"]
else:
    KIS_APP_KEY = ""
    KIS_APP_SECRET = ""
    KIS_ACCOUNT_NO = ""

KIS_VIRTUAL = os.getenv("KIS_VIRTUAL", "True").lower() in ("true", "1", "yes", "t")

# 텔레그램 설정
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# 설정값 검증용
def validate_config():
    if not KIS_SESSIONS:
        print("⚠️ 경고: 등록된 유효한 KIS 계좌 세션이 없습니다. .env 파일을 확인해주세요.")
    else:
        print(f"✅ {len(KIS_SESSIONS)}개의 계좌 세션이 로드되었습니다.")

if __name__ == "__main__":
    validate_config()
