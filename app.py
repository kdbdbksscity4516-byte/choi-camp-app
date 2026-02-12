import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
import requests

# 1. 설정 정보
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbypwwykL2zL54QN-6jb-zesuQB4-kS6NDDxhn2diMvUORHgdJbjjfCYrTqHWyWcEiZr/exec"

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")

# CSS: 버튼 레이아웃 최적화
st.markdown("""
    <style>
    .stButton > button { width: 100% !important; height: 45px !important; }
    div[data-testid="stMetricValue"] { font-size: 18px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚩 캠프 실시간 보고 시스템")

# 시트에 데이터 쓰는 함수
def send_to_sheet(row_idx, status):
    try:
        # Apps Script로 신호 전송 (row는 0부터 시작하므로 그대로 전달)
        response = requests.get(f"{script_url}?row={row_idx}&status={urllib.parse.quote(status)}")
        if response.status_code == 200:
            st.toast(f"✅ {status} 기록 완료!")
            return True
    except:
        st.error("기록에 실패했습니다. 인터넷 연결을 확인하세요.")
    return False

try:
    # 데이터 불러오기 (캐시 없이 실시간 로드)
    df = pd.read_csv(sheet_url)
    
    if not df.empty:
        # 데이터 전처리 (nan 제거)
        df = df.fillna("")
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        df['정렬용시간'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
        
        # 원본 시트의 인덱스를 유지하기 위해 reset_index 전의 번호를 보관
        df = df.sort_values(by=['날짜', '정렬용시간'])

        available_dates = sorted(df['날짜'].unique())
        today = datetime.now().date()
        default_idx = list(available_dates).index(today) if today in available_dates else 0
        selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
        st.divider()

        filtered_df = df[df['날짜'] == selected_date]

        for idx, row in filtered_df.iterrows():
            # 시트상의 실제 행 번호 계산 (헤더 제외 0부터 시작)
            # pandas의 인덱스가 원본 시트 인덱스와 일치한다고 가정
            actual_row_idx = idx 

            with st.container(border=True):
                # 1단: 시간 및 행사명
                title = row['행사명'] if row['행사명'] != "" else "일정 없음"
                st.markdown(f"### ⏱️ {row['시간']} | {title}")
                st.caption(f"📍 {row['주소']}")
                
                status = str(row.get('참석여부', '')).strip()
                if status == "" or status == "미체크":
                    status = "미체크"

                # 2단: 참석/불참/수정 로직
                if status == "미체크":
                    col1, col2 = st.columns(2)
                    if col1.button("🟢 참석", key=f"att_{idx}"):
                        if send_to_sheet(actual_row_idx, "참석"): st.rerun()
                    if col2.button("🔴 불참", key=f"no_{idx}"):
                        if send_to_sheet(actual_row_idx, "불참"): st.rerun()
                else:
                    res_col, edit_col = st.columns([3, 1])
                    with res_col:
                        if status == "참석": st.success(f"✅ 결과: {status}")
                        else: st.error(f"✅ 결과: {status}")
                    with edit_col:
                        if st.button("🔄 수정", key=f"edit_{idx}"):
                            if send_to_sheet(actual_row_idx, "미체크"): st.rerun()

                # 3단: 내비 버튼
                st.link_button("🚕 카카오내비 실행", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

except Exception as e:
    st.error(f"오류 발생: 시트에 '참석여부' 열이 있는지 확인해주세요.")
    
