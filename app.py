import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime

sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")

# --- UI 스타일 정리 ---
st.markdown("""
    <style>
    .stButton > button { width: 100% !important; height: 45px !important; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚩 캠프 실시간 보고")

# 세션 상태 초기화 (버튼 클릭 저장용)
if 'status_dict' not in st.session_state:
    st.session_state.status_dict = {}

try:
    df = pd.read_csv(sheet_url)
    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        df['정렬용시간'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
        df = df.sort_values(by=['날짜', '정렬용시간']).reset_index(drop=True)

        selected_date = st.selectbox("🗓️ 날짜 선택", sorted(df['날짜'].unique()))
        st.divider()

        filtered_df = df[df['날짜'] == selected_date]

        for idx, row in filtered_df.iterrows():
            with st.container(border=True):
                st.markdown(f"### ⏱️ {row['시간']} | {row['행사명']}")
                
                # 1. 상태 결정 (앱 내 세션 우선 -> 그 다음 시트 데이터)
                status_key = f"status_{selected_date}_{idx}"
                if status_key not in st.session_state.status_dict:
                    sheet_status = str(row.get('참석여부', '미체크')).strip()
                    st.session_state.status_dict[status_key] = sheet_status if sheet_status != 'nan' and sheet_status != '' else '미체크'
                
                current_status = st.session_state.status_dict[status_key]

                # 2. 상태에 따른 화면 표시
                if current_status == '미체크':
                    col1, col2 = st.columns(2)
                    if col1.button("🟢 참석", key=f"att_btn_{idx}"):
                        st.session_state.status_dict[status_key] = '참석'
                        st.rerun() # 화면 즉시 새로고침
                    if col2.button("🔴 불참", key=f"no_btn_{idx}"):
                        st.session_state.status_dict[status_key] = '불참'
                        st.rerun()
                else:
                    # 선택 완료 시 결과와 수정 버튼
                    res_col, edit_col = st.columns([3, 1])
                    with res_col:
                        if current_status == '참석': st.success(f"✅ 결과: {current_status}")
                        else: st.error(f"✅ 결과: {current_status}")
                    with edit_col:
                        if st.button("🔄 수정", key=f"edit_btn_{idx}"):
                            st.session_state.status_dict[status_key] = '미체크'
                            st.rerun()

                # 3. 내비 버튼
                st.link_button("🚕 카카오내비 실행", 
                               f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

except Exception as e:
    st.error("데이터 로딩 중...")
