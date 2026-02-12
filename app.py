import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime

sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 동선공유", layout="centered")
st.title("🚩 최웅식 캠프 실시간 보고")

try:
    df = pd.read_csv(sheet_url)
    if not df.empty:
        # 데이터 정렬
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        df['정렬용시간'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
        df = df.sort_values(by=['날짜', '정렬용시간']).reset_index()

        # 상단 날짜 선택
        available_dates = sorted(df['날짜'].unique())
        today = datetime.now().date()
        default_idx = list(available_dates).index(today) if today in available_dates else 0
        selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
        st.divider()

        filtered_df = df[df['날짜'] == selected_date]

        for idx, row in filtered_df.iterrows():
            with st.container(border=True):
                # --- 1단: 시간 및 행사명 ---
                st.markdown(f"### ⏱️ {row['시간']} | {row['행사명']}")
                st.caption(f"📍 {row['주소']}")
                
                # 가상의 상태 관리 (실제는 시트에서 가져옴)
                status = str(row.get('참석여부', '미체크'))
                if status == 'nan': status = '미체크'

                # --- 2단: 참석/불참 선택 또는 결과 표시 ---
                if status == '미체크':
                    # 아직 선택 안 했을 때: 버튼 2개가 나란히
                    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
                    if btn_col1.button("🟢 참석", key=f"att_{idx}", use_container_width=True):
                        st.toast("참석으로 기록합니다!") # 추후 시트 연동
                    if btn_col2.button("🔴 불참", key=f"no_{idx}", use_container_width=True):
                        st.toast("불참으로 기록합니다!")
                else:
                    # 이미 선택했을 때: 상태 글자 + 수정 버튼
                    res_col1, res_col2 = st.columns([3, 1])
                    with res_col1:
                        if status == '참석':
                            st.success(f"✅ 선택완료: {status}")
                        else:
                            st.error(f"✅ 선택완료: {status}")
                    with res_col2:
                        if st.button("🔄 수정", key=f"edit_{idx}", use_container_width=True):
                            st.toast("상태를 초기화합니다.") # 추후 시트 연동

                # --- 3단: 내비 실행 버튼 ---
                st.link_button("🚕 카카오내비 실행", 
                               f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}", 
                               use_container_width=True)

    else:
        st.warning("시트에 일정을 입력해주세요.")
except Exception as e:
    st.error("데이터 로딩 중... 시트에 '참석여부' 열이 있는지 확인해주세요.")
