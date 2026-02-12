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
                        st.link_button(f"🚕 내비 연결", f"https://map.kakao.com/link/search/{urllib.parse.quote(addr_val)}", use_container_width=True)
                    st.divider()
            
            # --- 경로 보기 로직 수정 (카카오맵 길찾기 웹 브라우저 방식) ---
            if len(addr_list) >= 2:
                # 첫 번째 주소를 출발지, 마지막을 도착지로 하고 나머지를 경유지로 보냅니다.
                start = urllib.parse.quote(addr_list[0])
                end = urllib.parse.quote(addr_list[-1])
                
                # 웹에서 바로 길찾기 결과를 보여주는 가장 확실한 링크입니다.
                # 모바일에서도 카카오맵 웹페이지가 열리며 경로가 그려집니다.
                kakao_route_url = f"https://map.kakao.com/?sName={start}&eName={end}"
                
                if len(addr_list) > 2:
                    # 경유지 추가 (vNames 파라미터 활용)
                    v_names = "|".join([urllib.parse.quote(a) for a in addr_list[1:-1]])
                    kakao_route_url += f"&vNames={v_names}"

                st.success("✅ 동선 지도가 준비되었습니다.")
                st.link_button(f"🗺️ {selected_date} 전체 경로 확인 (지도)", kakao_route_url, use_container_width=True, type="primary")
                st.caption("※ 버튼 클릭 후 '자동차' 아이콘을 누르면 선이 그려집니다.")
        else:
            st.warning("일정이 없습니다.")
except Exception as e:
    st.error("데이터 로딩 중...")
