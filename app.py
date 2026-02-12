import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime

sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 동선공유", layout="centered")
st.title("🚩 최웅식 캠프 동선공유")

try:
    df = pd.read_csv(sheet_url)
    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        df['정렬용시간'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
        df = df.sort_values(by=['날짜', '정렬용시간'])

        available_dates = sorted(df['날짜'].unique())
        today = datetime.now().date()
        default_idx = list(available_dates).index(today) if today in available_dates else 0

        selected_date = st.selectbox("📅 날짜 선택", available_dates, index=default_idx,
                                     format_func=lambda x: x.strftime('%m월 %d일 (%a)'))
        st.divider()

        filtered_df = df[df['날짜'] == selected_date]

        if not filtered_df.empty:
            addr_list = []
            for idx, row in filtered_df.iterrows():
                time_val = row.get('시간', '00:00')
                title_val = str(row.get('행사명', '장소')).strip()
                addr_val = str(row.get('주소', '')).strip()
                
                if addr_val and addr_val != 'nan':
                    addr_list.append(addr_val)

                with st.container():
                    col1, col2 = st.columns([1, 4])
                    col1.metric("시간", str(time_val))
                    with col2:
                        st.subheader(f"{title_val}")
                        st.write(f"📍 {addr_val}")
                        # 개별 장소는 여전히 카카오맵 검색으로 연결 (이게 제일 정확함)
                        st.link_button(f"🚕 내비 연결", f"https://map.kakao.com/link/search/{urllib.parse.quote(addr_val)}", use_container_width=True)
                    st.divider()
            
            # --- 전체 경로 보기 (구글 맵 지점 표시 방식) ---
            if addr_list:
                st.subheader("🗺️ 오늘의 전체 동선 요약")
                
                # 여러 지점을 한 지도에 표시하는 구글 맵 방식
                # 이 방식은 '길찾기'가 아니라 '지점 검색'이라서 선은 안 나오지만 핀은 확실히 찍힙니다.
                google_search_url = f"https://www.google.com/maps/search/{urllib.parse.quote('/'.join(addr_list))}"
                
                # 또는 더 확실한 구글 맵 리스트 공유 방식
                st.info("💡 아래 버튼을 누르면 오늘 방문할 모든 지점이 지도에 숫자로 찍혀서 나옵니다.")
                st.link_button(f"🚩 {selected_date} 전체 방문지 확인", google_search_url, use_container_width=True, type="primary")
        else:
            st.warning("일정이 없습니다.")
except Exception as e:
    st.error("데이터 로딩 중...")
