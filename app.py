import streamlit as st
import pandas as pd
import urllib.parse

sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 동선공유", layout="centered")
st.title("🚩 최웅식 캠프 동선공유")

try:
    df = pd.read_csv(sheet_url)
    if not df.empty:
        if '시간' in df.columns:
            df = df.sort_values(by=['시간'])
        
        for idx, row in df.iterrows():
            with st.container():
                time_val = row.get('시간', '00:00')
                title_val = row.get('행사명', '미정')
                addr_val = str(row.get('주소', '')).strip()

                st.subheader(f"⏱️ {time_val} | {title_val}")
                st.write(f"📍 {addr_val}")
                
                if addr_val and addr_val != 'nan':
                    # 장소명 빼고 '주소'만 인코딩해서 보냅니다. (이게 충돌이 제일 적습니다)
                    encoded_addr = urllib.parse.quote(addr_val)
                    
                    # 카카오맵 검색창에 바로 주소를 꽂아주는 링크입니다.
                    # 목적지 설정보다 이 방식이 주소 인식률이 훨씬 높습니다.
                    kakao_search_url = f"https://map.kakao.com/link/search/{encoded_addr}"
                    
                    st.link_button(f"🚕 {title_val} 내비 연결", kakao_search_url, use_container_width=True, type="primary")
                
                st.divider()
except Exception as e:
    st.error("데이터 로딩 중...")
