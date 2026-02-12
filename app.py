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
                title_val = row.get('행사명', '일정명 없음')
                addr_val = str(row.get('주소', '')).strip()

                st.subheader(f"⏱️ {time_val} | {title_val}")
                st.write(f"📍 {addr_val}")
                
                if addr_val and addr_val != 'nan':
                    # 한글 인코딩
                    encoded_name = urllib.parse.quote(title_val)
                    encoded_addr = urllib.parse.quote(addr_val)
                    
                    col1, col2 = st.columns(2)
                    
                    # 1. 카카오내비: 목적지(name)와 주소(address)를 명확히 구분해서 전달
                    kakao_link = f"https://map.kakao.com/link/to/{encoded_name},{encoded_addr}"
                    col1.link_button("🚕 카카오내비", kakao_link, use_container_width=True)
                    
                    # 2. 네이버 지도: 'search'가 아니라 'route' 모드로 직접 연결
                    # 이 링크는 앱이 열리면서 도착지에 주소를 강제로 넣습니다.
                    naver_link = f"https://map.naver.com/v5/directions/-/{{encoded_addr}},{{encoded_name}},,ADDRESS_ALL/car"
                    # 위 방식이 안될 경우를 대비한 검색형 길찾기 링크
                    naver_fallback = f"https://m.map.naver.com/route.nhn?menu=route&ename={encoded_name}&ex={encoded_addr}&pathType=0"
                    
                    col2.link_button("🅿️ 네이버 지도", naver_fallback, use_container_width=True)
                
                st.divider()
except Exception as e:
    st.error("데이터를 가져오는 중입니다. 잠시 후 새로고침 하세요.")
