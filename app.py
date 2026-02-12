import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
import requests

# 사무장님의 정보 (주소는 그대로 유지합니다)
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbypwwykL2zL54QN-6jb-zesuQB4-kS6NDDxhn2diMvUORHgdJbjjfCYrTqHWyWcEiZr/exec"

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")

st.title("🚩 캠프 실시간 보고 시스템")

# 시트에 기록하는 함수 (성공 여부 체크 강화)
def update_sheet(row_idx, status):
    try:
        # 0.5초 정도 짧게 대기하며 구글 서버에 신호 전송
        target_url = f"{script_url}?row={row_idx}&status={urllib.parse.quote(status)}"
        res = requests.get(target_url)
        if "성공" in res.text:
            return True
    except:
        pass
    return False

try:
    # 데이터 로드 (캐시 무시를 위해 시간 파라미터 추가)
    df = pd.read_csv(f"{sheet_url}&cachebust={datetime.now().timestamp()}")
    df = df.fillna("") # nan 방지

    if not df.empty:
        # 날짜 형식 변환
        df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
        
        # 오늘 날짜 선택
        available_dates = sorted(df['날짜_dt'].unique())
        today = datetime.now().date()
        default_idx = list(available_dates).index(today) if today in available_dates else 0
        selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
        st.divider()

        # 선택한 날짜의 데이터만 필터링 (원본 인덱스 보존)
        filtered_df = df[df['날짜_dt'] == selected_date]

        if not filtered_df.empty:
            for idx, row in filtered_df.iterrows():
                with st.container(border=True):
                    # 1단: 일정 정보
                    event_time = row['시간']
                    event_name = row['행사명'] if row['행사명'] != "" else "일정"
                    st.markdown(f"### ⏱️ {event_time} | {event_name}")
                    st.caption(f"📍 {row['주소']}")
                    
                    # 2단: 참석 상태 확인 및 버튼
                    current_status = str(row.get('참석여부', '미체크')).strip()
                    if current_status not in ["참석", "불참"]:
                        current_status = "미체크"

                    if current_status == "미체크":
                        c1, c2 = st.columns(2)
                        # 버튼 클릭 시 즉시 구글 시트로 전송
                        if c1.button("🟢 참석", key=f"at_{idx}", use_container_width=True):
                            if update_sheet(idx, "참석"): st.rerun()
                        if c2.button("🔴 불참", key=f"no_{idx}", use_container_width=True):
                            if update_sheet(idx, "불참"): st.rerun()
                    else:
                        # 이미 기록된 경우
                        r_col, e_col = st.columns([3, 1])
                        with r_col:
                            if current_status == "참석": st.success(f"✅ 결과: {current_status}")
                            else: st.error(f"✅ 결과: {current_status}")
                        with e_col:
                            if st.button("🔄 수정", key=f"ed_{idx}", use_container_width=True):
                                if update_sheet(idx, "미체크"): st.rerun()

                    # 3단: 내비
                    st.link_button("🚕 카카오내비 실행", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}", use_container_width=True)
        else:
            st.warning("선택한 날짜에 일정이 없습니다.")

except Exception as e:
    st.error(f"데이터를 불러오는 중입니다... 시트에 '참석여부' 열이 있는지 꼭 확인해 주세요!")
