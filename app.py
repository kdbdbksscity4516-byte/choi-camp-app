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
                    # 주소만 깔끔하게 리스트에 담기
                    addr_list.append(addr_val)

                with st.container():
                    col1, col2 = st.columns([1, 4])
                    col1.metric("시간", str(time_val))
                    with col2:
                        st.subheader(f"{title_val}")
                        st.write(f"📍 {addr_val}")
                        # 개별 내비는 가장 심플하게 주소 검색으로 연결
                        st.link_button(f"🚕 내비 연결", f"https://map.kakao.com/link/search/{urllib.parse.quote(addr_val)}", use_container_width=True)
                    st.divider()
            
            # --- 전체 경로 보기 로직 (가장 심플한 지도 공유 모드) ---
            if len(addr_list) >= 2:
                # 구글 맵의 '길찾기' 모드가 한국에서 선이 안 나오면, 
                # 카카오맵의 '여러 지점 표시' 기능을 활용합니다.
                # 주소들을 '/'로 연결하여 카카오맵 검색에 넣으면 지도에 핀들이 찍힙니다.
                combined_addr = "/".join(addr_list)
                kakao_multi_url = f"https://map.kakao.com/?q={urllib.parse.quote(combined_addr)}"
                
                st.success("✅ 전체 동선 확인 준비 완료")
                st.link_button(f"🗺️ {selected_date} 전체 경로 지도에서 보기", kakao_multi_url, use_container_width=True, type="primary")
                st.caption("※ 지도 앱이 열리면 검색 결과로 나온 장소들을 확인해 주세요.")
        else:
            st.warning("일정이 없습니다.")
except Exception as e:
    st.error("데이터 로딩 중...")
