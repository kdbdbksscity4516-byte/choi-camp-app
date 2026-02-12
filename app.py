import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime

# 시트 주소
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")

# --- 모바일에서 버튼을 무조건 좌우로 배치하는 마법의 코드 ---
st.markdown("""
    <style>
    [data-testid="column"] {
        width: calc(50% - 1rem) !important;
        flex: 1 1 calc(50% - 1rem) !important;
        min-width: calc(50% - 1rem) !important;
    }
    </style>
    """, unsafe_allow_stdio=True)

st.title("🚩 캠프 실시간 보고")

try:
    df = pd.read_csv(sheet_url)
    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        df['정렬용시간'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
        df = df.sort_values(by=['날짜', '정렬용시간']).reset_index()

        # 날짜 선택
        available_dates = sorted(df['날짜'].unique())
        today = datetime.now().date()
        default_idx = list(available_dates).index(today) if today in available_dates else 0
        selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
        st.divider()

        filtered_df = df[df['날짜'] == selected_date]

        for idx, row in filtered_df.iterrows():
            with st.container(border=True):
                # 1단: 시간과 행사명
                st.markdown(f"### ⏱️ {row['시간']} | {row['행사명']}")
                st.caption(f"📍 {row['주소']}")
                
                status = str(row.get('참석여부', '미체크')).strip()
                if status == 'nan' or status == '': status = '미체크'

                # 2단: 참석/불참 버튼 (무조건 좌우 배치)
                if status == '미체크':
                    col1, col2 = st.columns(2) 
                    with col1:
                        st.button("🟢 참석", key=f"att_{idx}", use_container_width=True)
                    with col2:
                        st.button("🔴 불참", key=f"no_{idx}", use_container_width=True)
                else:
                    # 선택 완료 시 결과와 수정 버튼
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
        st.warning("일정을 입력해주세요.")
except Exception as e:
    st.error("오류가 발생했습니다. 시트 설정을 확인해주세요.")
