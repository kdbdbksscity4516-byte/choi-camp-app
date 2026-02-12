import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
import requests

# 1. 설정 정보
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbxCGd8QvYAquyvkgb9fmc57XnEdham1TgbHMRqzQVcFbKOYToPlrOGE8E8B8KFS74b3/exec"

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")

# CSS: 새로고침 버튼을 우측 상단에 예쁘게 배치하고 버튼 디자인 조정
st.markdown("""
    <style>
    .stButton > button { width: 100% !important; }
    /* 새로고침 버튼 전용 스타일 */
    .refresh-btn > div > button {
        background-color: #f0f2f6 !important;
        color: #31333F !important;
        border-radius: 20px !important;
        border: 1px solid #dcdde1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 상단 헤더 및 새로고침 버튼 ---
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.title("🚩 캠프 보고")
with head_col2:
    st.write("") # 간격 맞춤용
    if st.button("🔄 새로고침", key="refresh_top"):
        st.rerun()

# 시트 기록 함수
def update_sheet_status(row_idx, status_text):
    api_url = f"{script_url}?row={row_idx+1}&status={urllib.parse.quote(status_text)}"
    try:
        res = requests.get(api_url, timeout=15)
        if "성공" in res.text:
            st.toast(f"✅ {status_text} 완료!")
            return True
        else:
            st.error(f"⚠️ 오류: {res.text}")
    except Exception as e:
        st.error(f"📡 연결 실패")
    return False

try:
    # 실시간 데이터 로드 (캐시 무시)
    df = pd.read_csv(f"{sheet_url}&t={datetime.now().timestamp()}")
    df = df.fillna("")

    if not df.empty:
        df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
        available_dates = sorted(df['날짜_dt'].unique())
        today = datetime.now().date()
        default_idx = list(available_dates).index(today) if today in available_dates else 0
        
        selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
        st.divider()

        filtered_df = df[df['날짜_dt'] == selected_date]

        for idx, row in filtered_df.iterrows():
            with st.container(border=True):
                # 1. 일정 정보
                st.markdown(f"### ⏱️ {row['시간']} | {row['행사명'] if row['행사명'] != '' else '일정'}")
                st.caption(f"📍 {row['주소']}")
                
                # 2. 참석여부 상태
                current_status = str(row.get('참석여부', '')).strip()
                if current_status not in ["참석", "불참"]: current_status = "미체크"

                # 3. 버튼 레이아웃
                if current_status == "미체크":
                    c1, c2 = st.columns(2)
                    if c1.button("🟢 참석", key=f"at_{idx}"):
                        if update_sheet_status(idx, "참석"): st.rerun()
                    if c2.button("🔴 불참", key=f"no_{idx}"):
                        if update_sheet_status(idx, "불참"): st.rerun()
                else:
                    r_col, e_col = st.columns([2, 1])
                    with r_col:
                        if current_status == "참석": st.success(f"✅ {current_status}")
                        else: st.error(f"✅ {current_status}")
                    with e_col:
                        if st.button("🔄 수정", key=f"ed_{idx}"):
                            if update_sheet_status(idx, "미체크"): st.rerun()

                # 4. 내비 버튼
                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}", use_container_width=True)
except Exception as e:
    st.error("데이터를 불러오는 중...")
