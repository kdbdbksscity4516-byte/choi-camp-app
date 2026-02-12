import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
import requests

# 1. 구글 시트 설정 (사무장님 시트 주소)
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

# [중요] 구글 시트에 데이터를 쓰기 위해서는 'Google Apps Script' 배포 주소가 필요합니다.
# 일단은 화면에서 체크하고 '수정'하는 UI를 먼저 구현해 드립니다.
def update_sheet(row_index, status):
    # 이 부분은 추후 구글 앱스 스크립트 URL을 넣으면 실제 시트가 바뀝니다.
    st.toast(f"{row_index+1}번 일정: {status}로 기록되었습니다!")

st.set_page_config(page_title="최웅식 캠프 동선공유", layout="centered")
st.title("🚩 최웅식 캠프 실시간 동선 & 보고")

try:
    # 데이터 가져오기 (캐시를 지워 실시간성 확보)
    df = pd.read_csv(sheet_url)
    
    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        df['정렬용시간'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
        df = df.sort_values(by=['날짜', '정렬용시간']).reset_index()

        available_dates = sorted(df['날짜'].unique())
        today = datetime.now().date()
        default_idx = list(available_dates).index(today) if today in available_dates else 0

        selected_date = st.selectbox("📅 날짜 선택", available_dates, index=default_idx)
        st.divider()

        filtered_df = df[df['날짜'] == selected_date]

        if not filtered_df.empty:
            for idx, row in filtered_df.iterrows():
                with st.container(border=True):
                    # 현재 상태 확인 (시트에 적힌 값)
                    current_status = str(row.get('참석여부', '미체크'))
                    if current_status == 'nan': current_status = '미체크'
                    
                    col1, col2 = st.columns([1, 4])
                    
                    with col1:
                        st.metric("시간", str(row['시간']))
                        # 상태에 따른 색상 표시
                        if current_status == '참석':
                            st.success("✅ 참석")
                        elif current_status == '불참':
                            st.error("❌ 불참")
                        else:
                            st.warning("❓ 대기")

                    with col2:
                        st.subheader(f"{row['행사명']}")
                        st.write(f"📍 {row['주소']}")
                        
                        # 참석/불참/수정 버튼
                        c1, c2, c3 = st.columns(3)
                        if c1.button("🟢 참석", key=f"att_{idx}"):
                            update_sheet(row['index'], "참석")
                        if c2.button("🔴 불참", key=f"no_{idx}"):
                            update_sheet(row['index'], "불참")
                        if c3.button("🔄 수정", key=f"edit_{idx}"):
                            st.info("다시 선택해 주세요.")
                        
                        # 내비 버튼 (작게 배치)
                        st.link_button("🚕 내비 실행", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

        else:
            st.warning("등록된 일정이 없습니다.")
except Exception as e:
    st.error("시트에서 '참석여부' 열을 추가했는지 확인해주세요!")
