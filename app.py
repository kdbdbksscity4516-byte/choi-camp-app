import streamlit as st
import pandas as pd
import urllib.parse

# 사무장님의 구글 시트 주소
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 동선공유", layout="centered")

st.title("🚩 최웅식 캠프 동선공유")
st.info("시트 수정 후 화면을 새로고침 해주세요.")

try:
    df = pd.read_csv(sheet_url)
    
    if not df.empty:
        # 시간순 정렬 (데이터가 있을 때만)
        if '시간' in df.columns:
            df = df.sort_values(by=['시간'])
        
        for idx, row in df.iterrows():
            with st.container():
                time_val = row.get('시간', '00:00')
                title_val = row.get('행사명', '일정명 없음')
                addr_val = str(row.get('주소', '')).strip()
                note_val = row.get('비고', '')

                st.subheader(f"⏱️ {time_val} | {title_val}")
                st.write(f"📍 {addr_val}")
                
                if addr_val and addr_val != 'nan':
                    # 카카오내비 전용 호출 주소 생성
                    # 이 코드는 앱을 직접 깨우고 목적지(q)를 강제로 입력합니다.
                    encoded_addr = urllib.parse.quote(addr_val)
                    kakao_navi_url = f"kakaonavi://search?q={encoded_addr}"
                    
                    # 만약 위 코드가 작동 안하는 환경을 위한 웹용 백업 주소
                    kakao_web_url = f"https://map.kakao.com/link/to/{urllib.parse.quote(title_val)},{encoded_addr}"
                    
                    # 실제 버튼 생성 (앱 호출 주소를 우선 사용)
                    st.link_button(f"🚕 {title_val} 내비 시작", kakao_navi_url, use_container_width=True, type="primary")
                    
                    # 팁: 위 버튼이 안될 경우를 대비해 작게 링크 하나 더 추가 (선택사항)
                    st.caption(f"[앱 실행이 안되면 클릭](https://map.kakao.com/link/to/{urllib.parse.quote(title_val)},{encoded_addr})")
                
                if pd.notna(note_val) and str(note_val) != 'nan':
                    st.info(f"💡 메모: {note_val}")
                
                st.divider()

        # 하단 전체 경로 확인 (구글맵)
        addresses = [str(a) for a in df['주소'].tolist() if pd.notna(a) and str(a).strip() != 'nan']
        if addresses:
            path = "/".join(addresses)
            map_url = f"https://www.google.com/maps/dir/{path}"
            st.link_button("🗺️ 오늘 전체 경로 한눈에 확인", map_url, use_container_width=True)
            
    else:
        st.warning("구글 시트에 일정을 입력해주세요.")

except Exception as e:
    st.error("데이터 로딩 중 오류가 발생했습니다.")
