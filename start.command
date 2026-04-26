#!/bin/bash
# 스트림릿 서버 실행 스크립트

echo "🚀 주말 자동매매 셋업 봇을 가동합니다..."
source "$(dirname "$0")/.venv/bin/activate"
streamlit run "$(dirname "$0")/app.py"
