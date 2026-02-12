import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime

sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")

# --- 버튼 가출 방지용 초정밀 CSS ---
st.markdown("""
    <style>
    /* 컬럼 간격 최소화 */
    [data-testid="column"] {
        width: 49% !important;
        flex: 1 1 49% !important;
        min-width: 45% !important;
        padding: 0 5px !important;
    }
    /* 버튼 내부 글자 크기 조정 */
    .stButton > button {
        font-size: 14px !important;
        padding: 5px !important;
        height: 40px !important;
    }
    /* 가로 배치 강제 고정 */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 5px !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚩 캠프 실시간 보고")

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
                st.caption(f"📍 {row['주소']}")
                
                status = str(row.get('참석여부', '미체크')).strip()
                if status == 'nan' or status == '': status = '미체크'

                if status == '미체크':
                    # 버튼을 감싸는 컬럼 생성
                    col1, col2 = st.columns(2)
                    with col1:
                        st.button("🟢 참석", key=f"att_{idx}", use_container_width=True)
                    with col2:
                        st.button("🔴 불참", key=f"no_{idx}", use_container_width=True)
                else:
                    res_col, edit_col = st.columns([2.5, 1.5])
                    with res_col:
                        if status == '참석': st.success(f"✅ {status}")
                        else: st.error(f"✅ {status}")
                    with edit_col:
                        st.button("🔄 수정", key=f"edit_{idx}", use_container_width=True)

                st.link_button("🚕 카카오내비 실행", 
                               f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}", 
                               use_container_width=True)
except Exception as e:
    st.error("데이터 로딩 중...")
