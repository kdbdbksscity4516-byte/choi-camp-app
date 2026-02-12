import streamlit as st
import pandas as pd
import urllib.parse

# 사무장님의 구글 시트 주소
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 동선공유", layout="centered")

st.title("🚩 최웅식 캠프 동선공유")

try:
    # 1. 데이터 가져오기
    df = pd.read_csv(sheet_url)
    
    if not df.empty:
        # 시간순 정렬
        if '시간' in df.columns:
            df = df.sort_values(by=['시간'])
        
        for idx, row in df.iterrows():
            with st.container():
                time_val = row.get('시간', '00:00')
                title_val = row.get('행사명', '미정')
                addr_val = str(row.get('주소', '')).strip()
                note_val = row.get('비고', '')

                st.subheader(f"⏱️ {time_val} | {title_val}")
                st.write(f"📍 {addr_val}")
                
                if addr_val and addr_val != 'nan':
                    # 카카오맵 '목적지 설정' 공식 웹 링크 (이게 가장 확실합니다)
                    # 주소와 장소명을 합쳐서 전달합니다.
                    query = f"{addr_val}"
                    kakao_final_url = f"https://map.kakao.com/link/to/{urllib.parse.quote(title_val)},{urllib.parse.quote(addr_val)}"
                    
                    # 버튼 생성
                    st.link_button(f"🚕 {title_val} 내비 시작", kakao_final_url, use_container_width=True, type="primary")
                
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
    st.error("데이터 로딩 중입니다. 잠시 후 새로고침 하세요.")
