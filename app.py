import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
import requests

# 1. 설정 정보
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbxCGd8QvYAquyvkgb9fmc57XnEdham1TgbHMRqzQVcFbKOYToPlrOGE8E8B8KFS74b3/exec"

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")

# CSS: 새로고침 버튼 포함 모든 버튼을 가로로 꽉 차게 설정
st.markdown("""
    <style>
    /* 모든 버튼 가로 100% 통일 */
    div.stButton > button {
        width: 100% !important;
        height: 50px !important;
        font-size: 16px !important;
        margin-top: 5px !important;
        margin-bottom: 5px !important;
        display: block !important;
    }
    /* 상단 영역 버튼 정렬 보정 */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 상단 헤더 ---
st.title("🚩 캠프 실시간 보고")

# 새로고침 버튼을 타이틀 바로 아래에 가로로 길게 배치
if st.button("🔄 페이지 새로고침", key="refresh_top"):
    st.rerun()

st.divider()

# 시트 기록 함수
def update_sheet_status(row_idx, status_text):
    api_url = f"{script_url}?row={row_idx+1}&status={urllib.parse.quote(status_text)}"
    try:
        res = requests.get(api_url, timeout=15)
        if "성공" in res.text:
            st.toast(f"✅ {status_text} 처리되었습니다.")
            return True
        else:
            st.error(f"⚠️ 오류: {res.text}")
    except Exception as e:
        st.error(f"📡 연결 실패")
    return False

try:
    df = pd.read_csv(f"{sheet_url}&t={datetime.now().timestamp()}")
    df = df.fillna("")

    if not df.empty:
        df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
        available_dates = sorted(df['날짜_dt'].unique())
        today = datetime.now().date()
        default_idx = list(available_dates).index(today) if today in available_dates else 0
        
        selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)

        filtered_df = df[df['날짜_dt'] == selected_date]

        for idx, row in filtered_df.iterrows():
            with st.container(border=True):
                # 1. 일정 정보
                st.markdown(f"### ⏱️ {row['시간']} | {row['행사명'] if row['행사명'] != '' else '일정'}")
                st.caption(f"📍 {row['주소']}")
                
                # 2. 참석여부 상태 확인
                current_status = str(row.get('참석여부', '')).strip()
                if current_status not in ["참석", "불참석"]: current_status = "미체크"

                # 3. 버튼 레이아웃 (가로로 길게 배치)
                if current_status == "미체크":
                    if st.button("🟢 참석", key=f"at_{idx}"):
                        if update_sheet_status(idx, "참석"): st.rerun()
                    if st.button("🔴 불참석", key=f"no_{idx}"):
                        if update_sheet_status(idx, "불참석"): st.rerun()
                else:
                    if current_status == "참석":
                        st.success(f"✅ 선택됨: {current_status}")
                    else:
                        st.error(f"✅ 선택됨: {current_status}")
                    
                    if st.button("🔄 수정하기", key=f"ed_{idx}"):
                        if update_sheet_status(idx, "미체크"): st.rerun()

                # 4. 내비 버튼
                st.link_button("🚕 카카오내비 실행", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}", use_container_width=True)
except Exception as e:
    st.error("데이터 로드 중...")
