import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
import requests

# 1. 설정 정보
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbxCGd8QvYAquyvkgb9fmc57XnEdham1TgbHMRqzQVcFbKOYToPlrOGE8E8B8KFS74b3/exec"

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")

# CSS: 모든 버튼을 가로로 꽉 차게 만들고 여백 조정
st.markdown("""
    <style>
    /* 모든 버튼 가로 100% */
    .stButton > button {
        width: 100% !important;
        height: 50px !important; /* 높이도 조금 더 키워서 누르기 편하게 */
        font-size: 16px !important;
        margin-top: 5px !important;
    }
    /* 성공/에러 박스도 가로 꽉 차게 */
    .stAlert {
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 상단 헤더 및 새로고침
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.title("🚩 캠프 보고")
with head_col2:
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

                # 3. 버튼 레이아웃 (가로로 길게 위아래 배치)
                if current_status == "미체크":
                    # 컬럼을 나누지 않고 바로 버튼을 배치하여 가로를 꽉 채움
                    if st.button("🟢 참석 완료", key=f"at_{idx}"):
                        if update_sheet_status(idx, "참석"): st.rerun()
                    if st.button("🔴 불참 (취소)", key=f"no_{idx}"):
                        if update_sheet_status(idx, "불참"): st.rerun()
                else:
                    # 선택 완료 시에도 가로로 배치
                    if current_status == "참석":
                        st.success(f"✅ 현재 상태: {current_status}")
                    else:
                        st.error(f"✅ 현재 상태: {current_status}")
                    
                    if st.button("🔄 기록 수정하기", key=f"ed_{idx}"):
                        if update_sheet_status(idx, "미체크"): st.rerun()

                # 4. 내비 버튼 (항상 가로 꽉 참)
                st.link_button("🚕 카카오내비 실행", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}", use_container_width=True)
except Exception as e:
    st.error("데이터 로드 중...")
