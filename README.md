# 📈 자동매매 시각화 및 주문 봇 V2 (Pro Edition)

한국투자증권(KIS) API 및 실시간 웹소켓을 연동하여 차트 시각화, 전략 시뮬레이션, 그리고 실제 주문 집행까지 지원하는 주식 트레이딩 플랫폼입니다.

## 🚀 주요 기능

### 1. 실시간 데이터 연동
- **웹소켓(WebSocket)**: 백그라운드 스레드 기반의 초고속 실시간 체결가 수신
- **계좌 연동**: 본인의 실제 예수금 및 보유 종목 상태를 실시간 트래킹

### 2. 스마트 분할 매매 전략
- **중기 채널 전략**: 1차(30%), 2차(60%), 3차(90%) 기하학적 타점 분할 진입
- **단기 돌파 전략**: 저항선 돌파 시 칼손절(-4%) 또는 여유손절(-10%) 맞춤형 대응
- **트레일링 바이**: 타점 도달 후 **1% 반등 확인 시** 안전 매수

---

## 🛠️ 설치 및 실행 방법

### 1. 종속성 라이브러리 설치
```bash
pip install -r requirements.txt
pip install websockets
```

### 2. 환경 변수 설정 (`.env`)
프로젝트 루트에 `.env` 파일을 생성하고 계좌 정보를 입력합니다.
```env
KIS_ACC1_KEY=여러분의_API_KEY
KIS_ACC1_SECRET=여러분의_SECRET
KIS_ACC1_NO=계좌번호-01
KIS_ACC1_NAME=계좌별칭

KIS_VIRTUAL=False # True: 모의투자 / False: 실전투자
```

### 3. 프로그램 실행
```bash
streamlit run app.py
```

---

## 📂 핵심 파일 구조
- `app.py`: 메인 웹 애플리케이션 엔진
- `calculator.py`: 리스크 관리 및 분할 매수 가격 연산 모듈
- `kis_client.py`: 증권사 API 통신 클라이언트
- `kis_websocket.py`: 비동기 시세 데이터 통신망
- `components/`: 레이아웃 전용 UI 파일 모음
