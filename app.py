import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime

sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 동선공유", layout="centered")

# --- 앱 상단 제목 ---
st.title("🚩 최웅식 캠프 동선공유")

try:
    # 1. 데이터 가져오기 및 전처리
    df = pd.read_csv(sheet_url)
    if not df.empty:
        # 날짜 형식 변환 및 정렬
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        df['정렬용시간'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
        df = df.sort_values(by=['날짜', '정렬용시간'])

        # 2. 날짜 선택 영역 (화면 상단에 배치)
        available_dates = sorted(df['날짜'].unique())
        
        # 오늘 날짜를 기본값으로, 없으면 첫 번째 날짜 선택
        today = datetime.now().date()
        default_idx = 0
        if today in available_dates:
            default_idx = list(available_dates).index(today)

        # 화면 상단에 가로로 날짜 선택 버튼 배치
        st.write("📅 **조회할 날짜를 선택하세요**")
        selected_date = st.selectbox(
            "날짜 선택", 
            available_dates, 
            index=default_idx,
            format_func=lambda x: x.strftime('%m월 %d일 (%a)'),
            label_visibility="collapsed" # 라벨 숨김으로 깔끔하게
        )

        st.markdown(f"### 📍 {selected_date.strftime('%m월 %d일')} 일정")
        st.divider()

        # 3. 선택한 날짜로 필터링하여 일정 표시
        filtered_df = df[df['날짜'] == selected_date]

        if not filtered_df.empty:
            for idx, row in filtered_df.iterrows():
                with st.container():
                    time_val = row.get('시간', '00:00')
                    title_val = row.get('행사명', '미정')
                    addr_val = str(row.get('주소', '')).strip()
                    note_val = row.get('비고', '')

                    col1, col2 = st.columns([1, 4])
                    col1.metric("시간", str(time_val))
                    
                    with col2:
                        st.subheader(f"{title_val}")
                        st.write(f"📍 {addr_val}")
                        
                        if addr_val and addr_val != 'nan':
                            encoded_addr = urllib.parse.quote(addr_val)
                            # 주소 검색창으로 바로 연결되는 방식 (성공률 제일 높음)
                            kakao_search_url = f"https://map.kakao.com/link/search/{encoded_addr}"
                            st.link_button(f"🚕 내비 연결", kakao_search_url, use_container_width=True)
                    
                    if pd.notna(note_val) and str(note_val) != 'nan':
                        st.info(f"💡 메모: {note_val}")
                    st.divider()
            
            # 하단 전체 경로 보기
            addresses = [str(a) for a in filtered_df['주소'].tolist() if pd.notna(a) and str(a).strip() != 'nan']
            if addresses:
                path = "/".join(addresses)
                map_url = f"https://www.google.com/maps/dir/{path}"
                st.link_button("🗺️ 오늘 전체 경로 한눈에 확인", map_url, use_container_width=True)
        else:
            st.warning("선택하신 날짜에는 등록된 일정이 없습니다.")
            
    else:
        st.warning("구글 시트에 일정을 입력해주세요.")

except Exception as e:
    st.error("데이터 로딩 중... 시트의 날짜 형식을 확인해주세요 (예: 2026-02-12)")
