import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime

# 사무장님의 구글 시트 주소
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")

# --- 에러 원인이었던 부분 수정: 모바일 버튼 좌우 고정용 CSS ---
st.markdown("""
    <style>
    [data-testid="column"] {
        width: 48% !important;
        flex: 1 1 48% !important;
        min-width: 48% !important;
        display: inline-block !important;
    }
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
    }
    </style>
    """, unsafe_allow_html=True) # 여기서 stdio가 아니라 html이어야 에러가 안 납니다!

st.title("🚩 캠프 실시간 보고")

try:
    df = pd.read_csv(sheet_url)
    if not df.empty:
        # 데이터 전처리
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        df['정렬용시간'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
        df = df.sort_values(by=['날짜', '정렬용시간']).reset_index(drop=True)

        # 상단 날짜 선택
        available_dates = sorted(df['날짜'].unique())
        today = datetime.now().date()
        default_idx = list(available_dates).index(today) if today in available_dates else 0
        selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
        st.divider()

        filtered_df = df[df['날짜'] == selected_date]

        if not filtered_df.empty:
            for idx, row in filtered_df.iterrows():
                with st.container(border=True):
                    # 1단: 시간 및 행사명
                    st.markdown(f"### ⏱️ {row['시간']} | {row['행사명']}")
                    st.caption(f"📍 {row['주소']}")
                    
                    # 참석여부 열이 없으면 '미체크'로 기본값 설정
                    status = str(row.get('참석여부', '미체크')).strip()
                    if status == 'nan' or status == '': status = '미체크'

                    # 2단: 참석/불참 버튼 (무조건 좌우 나란히)
                    if status == '미체크':
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            st.button("🟢 참석", key=f"att_{idx}", use_container_width=True)
                        with btn_col2:
                            st.button("🔴 불참", key=f"no_{idx}", use_container_width=True)
                    else:
                        # 이미 선택했을 때
                        res_col, edit_col = st.columns([2, 1])
                        with res_col:
                            if status == '참석':
                                st.success(f"✅ {status}")
                            else:
                                st.error(f"✅ {status}")
                        with edit_col:
                            st.button("🔄 수정", key=f"edit_{idx}", use_container_width=True)

                    # 3단: 내비 실행 버튼
                    st.link_button("🚕 카카오내비 실행", 
                                   f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}", 
                                   use_container_width=True)
        else:
            st.warning("등록된 일정이 없습니다.")
            
except Exception as e:
    st.error(f"시트 데이터를 읽는 중 오류가 발생했습니다. '참석여부' 칸을 확인해 주세요.")
