import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
import requests

# 1. 사무장님이 새로 주신 URL로 교체했습니다.
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbxCGd8QvYAquyvkgb9fmc57XnEdham1TgbHMRqzQVcFbKOYToPlrOGE8E8B8KFS74b3/exec"

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")
st.title("🚩 캠프 실시간 보고 시스템")

# 시트 기록 함수
def update_sheet_status(row_idx, status_text):
    # 인덱스 보정: pandas 인덱스 + 1 (헤더가 1번줄이므로)
    api_url = f"{script_url}?row={row_idx+1}&status={urllib.parse.quote(status_text)}"
    try:
        # 타임아웃을 넉넉히 주어 연결 안정성을 높입니다.
        res = requests.get(api_url, timeout=15)
        if "성공" in res.text:
            st.toast(f"✅ {status_text} 기록 완료!")
            return True
        else:
            st.error(f"⚠️ 시트 응답 오류: {res.text}")
    except Exception as e:
        st.error(f"📡 전송 실패 (인터넷 연결 확인): {e}")
    return False

try:
    # 캐시 방지용 파라미터를 추가하여 실시간 시트 데이터를 읽어옵니다.
    df = pd.read_csv(f"{sheet_url}&t={datetime.now().timestamp()}")
    df = df.fillna("") # 빈칸(nan) 처리

    if not df.empty:
        # 날짜 데이터 처리
        df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
        available_dates = sorted(df['날짜_dt'].unique())
        today = datetime.now().date()
        default_idx = list(available_dates).index(today) if today in available_dates else 0
        
        selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
        st.divider()

        # 선택한 날짜의 데이터만 필터링
        filtered_df = df[df['날짜_dt'] == selected_date]

        if not filtered_df.empty:
            for idx, row in filtered_df.iterrows():
                with st.container(border=True):
                    # 1. 일정 정보 표시
                    event_time = row['시간']
                    event_name = row['행사명'] if row['행사명'] != "" else "일정"
                    st.markdown(f"### ⏱️ {event_time} | {event_name}")
                    st.caption(f"📍 {row['주소']}")
                    
                    # 2. 참석여부 상태 확인
                    current_status = str(row.get('참석여부', '')).strip()
                    if current_status not in ["참석", "불참"]: 
                        current_status = "미체크"

                    # 3. UI 구성 (버튼 또는 결과 표시)
                    if current_status == "미체크":
                        c1, c2 = st.columns(2)
                        # 원본 시트의 인덱스(idx)를 사용하여 정확한 행에 기록합니다.
                        if c1.button("🟢 참석", key=f"at_{idx}", use_container_width=True):
                            if update_sheet_status(idx, "참석"):
                                st.rerun()
                        if c2.button("🔴 불참", key=f"no_{idx}", use_container_width=True):
                            if update_sheet_status(idx, "불참"):
                                st.rerun()
                    else:
                        # 이미 선택된 경우: 결과 표시 및 수정 버튼
                        r_col, e_col = st.columns([3, 1])
                        with r_col:
                            if current_status == "참석":
                                st.success(f"✅ 결과: {current_status}")
                            else:
                                st.error(f"✅ 결과: {current_status}")
                        with e_col:
                            if st.button("🔄 수정", key=f"ed_{idx}", use_container_width=True):
                                if update_sheet_status(idx, "미체크"):
                                    st.rerun()

                    # 4. 내비 실행 버튼
                    st.link_button("🚕 카카오내비 실행", 
                                   f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}", 
                                   use_container_width=True)
        else:
            st.warning("선택한 날짜에 일정이 없습니다.")

except Exception as e:
    st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
