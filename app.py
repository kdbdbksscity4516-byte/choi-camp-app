import streamlit as st
import pandas as pd
import urllib.parse

sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 동선공유", layout="centered")
st.title("🚩 최웅식 캠프 동선공유")

try:
    df = pd.read_csv(sheet_url)
    
    if not df.empty:
        # 1. 날짜와 시간 정렬 (날짜 먼저, 그 다음 시간순)
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        df['정렬용시간'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
        df = df.sort_values(by=['날짜', '정렬용시간'])

        current_date = None

        for idx, row in df.iterrows():
            # 2. 날짜가 바뀌면 날짜 헤더 출력
            if row['날짜'] != current_date:
                current_date = row['날짜']
                st.markdown(f"### 📅 {current_date}")
                st.markdown("---")

            with st.container():
                time_val = row.get('시간', '00:00')
                title_val = row.get('행사명', '미정')
                addr_val = str(row.get('주소', '')).strip()

                # 카드 형태 구성
                col1, col2 = st.columns([1, 4])
                col1.metric("시간", str(time_val))
                
                with col2:
                    st.subheader(f"{title_val}")
                    st.write(f"📍 {addr_val}")
                    
                    if addr_val and addr_val != 'nan':
                        encoded_addr = urllib.parse.quote(addr_val)
                        kakao_search_url = f"https://map.kakao.com/link/search/{encoded_addr}"
                        st.link_button(f"🚕 내비 연결", kakao_search_url, use_container_width=True)
                st.write("") # 간격 조절
                
    else:
        st.warning("구글 시트에 일정을 입력해주세요.")

except Exception as e:
    st.info("시트 데이터를 읽어오는 중입니다. '날짜' 열에 2026-02-12 형태로 입력되었는지 확인해주세요.")
