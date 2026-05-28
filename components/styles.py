import streamlit as st

def apply_custom_styles():
    st.markdown("""
        <style>
        .main { background-color: #0e1117; }
        .stMetric { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #2a2e39; }
        div[data-testid="stExpander"] { border: 1px solid #2a2e39; border-radius: 10px; }
        
        /* 여백 최소화 (상단 바 가림 방지) */
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"],
        .block-container {
            padding-top: 3rem !important;
            padding-bottom: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        /* 1. 전체 컴포넌트 간 수직 간격 축소 */
        div[data-testid="stVerticalBlock"] {
            gap: 0.7rem !important;
        }
        
        /* 2. 구분선(hr) 상하 여백 축소 */
        hr {
            margin-top: 7px !important;
            margin-bottom: 7px !important;
            border-color: #2a2e39 !important;
        }
        
        /* 3. 멀티셀렉트(목표가) 박스 높이/패딩 축소 */
        div[data-testid="stMultiSelect"] > div:first-child {
            padding: 0px !important;
            min-height: 24px !important;
        }
        div[data-testid="stMultiSelect"] div[role="button"] {
            padding: 1px 4px !important;
            min-height: 22px !important;
            font-size: 0.75rem !important;
        }
        div[data-testid="stMultiSelect"] span {
            font-size: 0.75rem !important;
        }
        
        /* 입력 박스 크기/폰트 축소 */
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stDateInput"] input {
            font-size: 0.8rem !important;
            padding: 4px 8px !important;
            height: 30px !important;
        }
        div[data-testid="stTextInput"] div[role="group"],
        div[data-testid="stNumberInput"] div[role="group"],
        div[data-testid="stDateInput"] div[role="group"] {
            height: 30px !important;
            min-height: 30px !important;
        }
        div[data-testid="stTextInput"] > div,
        div[data-testid="stNumberInput"] > div,
        div[data-testid="stDateInput"] > div {
            height: 30px !important;
            min-height: 30px !important;
            overflow: hidden !important;
        }
        /* selectbox 높이 축소 */
        div[data-testid="stSelectbox"] > div > div {
            height: 30px !important;
            min-height: 30px !important;
        }
        div[data-testid="stSelectbox"] > div > div > div {
            font-size: 0.8rem !important;
            padding: 2px 8px !important;
        }
        
        /* 입력창 라벨 폰트 축소 및 여백 제거 */
        div[data-testid="stNumberInput"] label {
            font-size: 0.75rem !important;
            margin-bottom: 0px !important;
            padding-bottom: 2px !important;
        }
        
        /* 컨테이너 테두리 내부 여백 축소 */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 10px !important;
        }
        
        /* 숫자 입력 박스 +, - 버튼 숨기기 */
        button[data-testid="stNumberInputStepDown"],
        button[data-testid="stNumberInputStepUp"] {
            display: none !important;
        }
        /* 버튼이 사라진 공간만큼 입력창 너비 확장 */
        div[data-testid="stNumberInput"] div[role="group"] > div {
            width: 100% !important;
        }

        /* data_editor 컬럼 헤더 타입 아이콘 숨기기 */
        [data-testid="stDataFrameResizable"] [role="columnheader"] svg {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
