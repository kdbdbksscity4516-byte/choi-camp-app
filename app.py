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
            # 경로 생성을 위해 (장소명, 주소) 쌍을 리스트로 저장
            route_points = []
            
            for idx, row in filtered_df.iterrows():
                time_val = row.get('시간', '00:00')
                title_val = str(row.get('행사명', '장소')).strip()
                addr_val = str(row.get('주소', '')).strip()
                
                if addr_val and addr_val != 'nan':
                    route_points.append((title_val, addr_val))

                with st.container():
                    col1, col2 = st.columns([1, 4])
                    col1.metric("시간", str(time_val))
                    with col2:
                        st.subheader(f"{title_val}")
                        st.write(f"📍 {addr_val}")
                        # 개별 내비는 검색창으로 연결 (가장 확실함)
                        st.link_button(f"🚕 내비 연결", f"https://map.kakao.com/link/search/{urllib.parse.quote(addr_val)}", use_container_width=True)
                    st.divider()
            
            # --- 경로 자동 생성 로직 수정 ---
            if len(route_points) >= 2:
                # 시작점과 도착점 설정
                s_name, s_addr = route_points[0]
                e_name, e_addr = route_points[-1]
                
                # 카카오맵 길찾기 URL (이름과 주소를 함께 전송해야 경로가 바로 뜹니다)
                # 형식: /from/이름,주소/to/이름,주소
                kakao_route_url = f"https://map.kakao.com/link/from/{urllib.parse.quote(s_name)},{urllib.parse.quote(s_addr)}/to/{urllib.parse.quote(e_name)},{urllib.parse.quote(e_addr)}"
                
                # 경유지가 있다면 추가
                if len(route_points) > 2:
                    v_list = []
                    for v_name, v_addr in route_points[1:-1]:
                        v_list.append(f"{urllib.parse.quote(v_name)},{urllib.parse.quote(v_addr)}")
                    kakao_route_url += "?via=" + "|".join(v_list)
                
                st.success("✅ 오늘의 전체 경로가 준비되었습니다.")
                st.link_button(f"🗺️ {selected_date} 전체 동선 선 연결 보기", kakao_route_url, use_container_width=True, type="primary")
        else:
            st.warning("일정이 없습니다.")
except Exception as e:
    st.error("데이터 로딩 중...")
