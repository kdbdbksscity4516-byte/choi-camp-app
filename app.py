import streamlit as st
import pandas as pd
import urllib.parse

# 사무장님의 구글 시트 주소
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 동선공유", layout="centered")

st.title("🚩 최웅식 캠프 동선공유")
st.info("구글 시트 수정 후 '새로고침'을 누르면 반영됩니다.")

try:
    df = pd.read_csv(sheet_url)
    
    if not df.empty:
        # 시간순 정렬
        if '시간' in df.columns:
            df = df.sort_values(by=['시간'])
        
        for idx, row in df.iterrows():
            with st.container():
                time_val = row.get('시간', '00:00')
                title_val = row.get('행사명', '일정명 없음')
                addr_val = str(row.get('주소', ''))
                note_val = row.get('비고', '')

                col1, col2 = st.columns([1, 4])
                col1.metric("시간", str(time_val))
                
                with col2:
                    st.subheader(f"{title_val}")
                    st.write(f"📍 {addr_val}")
                    
                    if addr_val and addr_val.strip() != 'nan':
                        # 카카오내비 목적지 공유 링크 생성
                        encoded_addr = urllib.parse.quote(addr_val)
                        encoded_name = urllib.parse.quote(title_val)
                        kakao_url = f"https://map.kakao.com/link/to/{encoded_name},{encoded_addr}"
                        
                        # 버튼 배치
                        st.link_button(f"🚕 {title_val} 내비 연결", kakao_url, use_container_width=True)
                    
                    if pd.notna(note_val) and str(note_val) != 'nan':
                        st.caption(f"💬 {note_val}")
                st.divider()

        # 하단 전체 동선 요약 (구글 맵)
        addresses = [str(a) for a in df['주소'].tolist() if pd.notna(a) and str(a).strip() != 'nan']
        if addresses:
            path = "/".join(addresses)
            map_url = f"https://www.google.com/maps/dir/{path}"
            st.link_button("🗺️ 전체 경로 한눈에 보기 (구글맵)", map_url, use_container_width=True)
            
    else:
        st.warning("구글 시트에 데이터를 입력해주세요.")

except Exception as e:
    st.error("데이터 로딩 중 오류가 발생했습니다.")
    st.write(e)
