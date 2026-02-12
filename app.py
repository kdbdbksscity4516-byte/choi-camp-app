import streamlit as st
import pandas as pd
import urllib.parse

sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 동선공유", layout="centered")
st.title("🚩 최웅식 캠프 동선공유")

try:
    df = pd.read_csv(sheet_url)
    
    if not df.empty:
        # 1. 시간 정렬 로직 추가
        # '시간' 컬럼을 실제 시간 데이터로 변환하여 정렬합니다.
        df['정렬용시간'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
        df = df.sort_values(by=['정렬용시간'])

        for idx, row in df.iterrows():
            with st.container():
                time_val = row.get('시간', '00:00')
                title_val = row.get('행사명', '미정')
                addr_val = str(row.get('주소', '')).strip()

                st.subheader(f"⏱️ {time_val} | {title_val}")
                st.write(f"📍 {addr_val}")
                
                if addr_val and addr_val != 'nan':
                    encoded_addr = urllib.parse.quote(addr_val)
                    kakao_search_url = f"https://map.kakao.com/link/search/{encoded_addr}"
                    st.link_button(f"🚕 {title_val} 내비 연결", kakao_search_url, use_container_width=True, type="primary")
                
                st.divider()
    else:
        st.warning("구글 시트에 일정을 입력해주세요.")

except Exception as e:
    # 에러 메시지를 조금 더 친절하게 바꿨습니다.
    st.info("시트 데이터를 불러오는 중입니다. 잠시만 기다려주세요.")
