import streamlit as st
import pandas as pd
import urllib.parse

# 사무장님의 구글 시트 주소
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 동선공유", layout="centered")

st.title("🚩 최웅식 캠프 동선공유")
st.markdown("---")

try:
    df = pd.read_csv(sheet_url)
    
    if not df.empty:
        if '시간' in df.columns:
            df = df.sort_values(by=['시간'])
        
        for idx, row in df.iterrows():
            with st.container():
                time_val = row.get('시간', '00:00')
                title_val = row.get('행사명', '일정명 없음')
                addr_val = str(row.get('주소', ''))
                note_val = row.get('비고', '')

                st.subheader(f"⏱️ {time_val} | {title_val}")
                st.write(f"📍 {addr_val}")
                
                if addr_val and addr_val.strip() != 'nan':
                    # 주소 인코딩
                    encoded_name = urllib.parse.quote(title_val)
                    encoded_addr = urllib.parse.quote(addr_val)
                    
                    btn_col1, btn_col2 = st.columns(2)
                    
                    # 1. 카카오내비 (앱 호출 전용 주소)
                    # 이 방식은 앱을 직접 깨워 목적지 입력 화면까지 보냅니다.
                    kakao_app_url = f"kakaonavi://search?q={encoded_addr}"
                    # 만약 앱이 없는 경우를 대비한 웹 링크
                    kakao_web_url = f"https://map.kakao.com/link/to/{encoded_name},{encoded_addr}"
                    
                    btn_col1.link_button("🚕 카카오내비", kakao_web_url, use_container_width=True)
                    
                    # 2. 네이버 지도 (길찾기 바로 연결)
                    # 네이버 지도 앱의 '장소 검색 후 길찾기' 파라미터를 강화했습니다.
                    naver_app_url = f"nmap://search?query={encoded_addr}&appname=choi-camp"
                    naver_web_url = f"https://map.naver.com/v5/search/{encoded_addr}"
                    
                    btn_col2.link_button("🅿️ 네이버 지도", naver_web_url, use_container_width=True)
                
                if pd.notna(note_val) and str(note_val) != 'nan':
                    st.info(f"💡 메모: {note_val}")
                
                st.divider()

        # 하단 구글맵 통합 경로
        addresses = [str(a) for a in df['주소'].tolist() if pd.notna(a) and str(a).strip() != 'nan']
        if addresses:
            path = "/".join(addresses)
            map_url = f"https://www.google.com/maps/dir/{path}"
            st.link_button("🗺️ 오늘 전체 경로 한눈에 확인", map_url, use_container_width=True)
            
    else:
        st.warning("구글 시트에 일정을 입력해주세요.")

except Exception as e:
    st.error("데이터 로딩 중 오류가 발생했습니다.")
