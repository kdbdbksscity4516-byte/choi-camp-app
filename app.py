import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta, timezone # 시간대 설정 추가
import requests

# 1. 설정 정보
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbxCGd8QvYAquyvkgb9fmc57XnEdham1TgbHMRqzQVcFbKOYToPlrOGE8E8B8KFS74b3/exec"

# 한국 시간(KST) 설정: UTC+9
KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)
today_kst = now_kst.date()

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")

# CSS: 버튼 가로 100%
st.markdown("""
    <style>
    div.stButton > button {
        width: 100% !important;
        height: 50px !important;
        font-size: 16px !important;
        margin-top: 5px !important;
        margin-bottom: 5px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚩 캠프 실시간 보고")

# 시트 기록 함수
def update_sheet_status(row_idx, status_text):
    api_url = f"{script_url}?row={row_idx+1}&status={urllib.parse.quote(status_text)}"
    try:
        res = requests.get(api_url, timeout=15)
        if "성공" in res.text:
            st.toast(f"✅ {status_text} 처리되었습니다.")
            return True
    except:
        st.error("📡 연결 실패")
    return False

try:
    # 데이터 로드
    df = pd.read_csv(f"{sheet_url}&t={now_kst.timestamp()}")
    df = df.fillna("")

    if not df.empty:
        # 시간 정렬 로직
        df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
        df['temp_time'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
        df = df.sort_values(by=['날짜_dt', 'temp_time']).reset_index()

        # --- 상단 UI 배치 (오늘 날짜 자동 선택 보정) ---
        available_dates = sorted(df['날짜_dt'].unique())
        
        # 오늘 날짜(13일)가 목록에 있으면 그 번호를, 없으면 0번을 선택
        if today_kst in available_dates:
            default_idx = list(available_dates).index(today_kst)
        else:
            default_idx = 0
        
        # 1. 날짜 선택
        selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)

        # 2. 페이지 새로고침
        if st.button("🔄 페이지 새로고침", key="refresh_top"):
            st.rerun()

        st.divider()

        # 선택한 날짜 필터링
        filtered_df = df[df['날짜_dt'] == selected_date]

        if not filtered_df.empty:
            for _, row in filtered_df.iterrows():
                orig_idx = row['index'] 
                with st.container(border=True):
                    st.markdown(f"### ⏱️ {row['시간']} | {row['행사명'] if row['행사명'] != '' else '일정'}")
                    st.caption(f"📍 {row['주소']}")
                    
                    current_status = str(row.get('참석여부', '')).strip()
                    if current_status not in ["참석", "불참석"]: current_status = "미체크"

                    if current_status == "미체크":
                        if st.button("🟢 참석", key=f"at_{orig_idx}"):
                            if update_sheet_status(orig_idx, "참석"): st.rerun()
                        if st.button("🔴 불참석", key=f"no_{orig_idx}"):
                            if update_sheet_status(orig_idx, "불참석"): st.rerun()
                    else:
                        if current_status == "참석": st.success(f"✅ 선택됨: {current_status}")
                        else: st.error(f"✅ 선택됨: {current_status}")
                        
                        if st.button("🔄 수정하기", key=f"ed_{orig_idx}"):
                            if update_sheet_status(orig_idx, "미체크"): st.rerun()

                    st.link_button("🚕 카카오내비 실행", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")
        else:
            st.warning("선택한 날짜에 일정이 없습니다.")

except Exception as e:
    st.error(f"오류 발생: {e}")
