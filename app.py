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

        st.write("📅 **조회할 날짜를 선택하세요**")
        selected_date = st.selectbox("날짜 선택", available_dates, index=default_idx,
                                     format_func=lambda x: x.strftime('%m월 %d일 (%a)'),
                                     label_visibility="collapsed")

        st.markdown(f"### 📍 {selected_date.strftime('%m월 %d일')} 일정")
        st.divider()

        filtered_df = df[df['날짜'] == selected_date]

        if not filtered_df.empty:
            addr_list = [] # 경로 생성을 위한 주소 리스트
            
            for idx, row in filtered_df.iterrows():
                with st.container():
                    time_val = row.get('시간', '00:00')
                    title_val = row.get('행사명', '미정')
                    addr_val = str(row.get('주소', '')).strip()
                    
                    if addr_val and addr_val != 'nan':
                        addr_list.append(addr_val) # 주소 저장

                    col1, col2 = st.columns([1, 4])
                    col1.metric("시간", str(time_val))
                    
                    with col2:
                        st.subheader(f"{title_val}")
                        st.write(f"📍 {addr_val}")
                        
                        if addr_val and addr_val != 'nan':
                            encoded_addr = urllib.parse.quote(addr_val)
                            kakao_search_url = f"https://map.kakao.com/link/search/{encoded_addr}"
                            st.link_button(f"🚕 내비 연결", kakao_search_url, use_container_width=True)
                    st.divider()
            
            # --- 수정된 전체 경로 보기 로직 (카카오맵 경유지 활용) ---
            if len(addr_list) >= 2:
                # 시작점, 경유지들, 도착점을 구분해서 링크 생성
                start_addr = urllib.parse.quote(addr_list[0])
                dest_addr = urllib.parse.quote(addr_list[-1])
                waypoint_str = ""
                if len(addr_list) > 2:
                    # 중간 주소들을 경유지로 추가
                    waypoints = [urllib.parse.quote(a) for a in addr_list[1:-1]]
                    waypoint_str = "&via=" + ",".join(waypoints)
                
                # 카카오맵 자동차 길찾기 공식 링크
                kakao_route_url = f"https://map.kakao.com/link/from/{start_addr}/to/{dest_addr}{waypoint_str}"
                
                st.info("💡 아래 버튼을 누르면 오늘의 전체 동선이 지도로 그려집니다.")
                st.link_button(f"🗺️ {selected_date} 전체 동선 확인 (카카오맵)", kakao_route_url, use_container_width=True, type="secondary")
        else:
            st.warning("선택하신 날짜에는 등록된 일정이 없습니다.")
except Exception as e:
    st.error("데이터 로딩 중...")
