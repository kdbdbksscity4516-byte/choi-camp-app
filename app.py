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
            name_list = []
            for idx, row in filtered_df.iterrows():
                time_val = row.get('시간', '00:00')
                title_val = str(row.get('행사명', '장소')).strip()
                addr_val = str(row.get('주소', '')).strip()
                
                if addr_val and addr_val != 'nan':
                    addr_list.append(addr_val)
                    name_list.append(title_val)

                with st.container():
                    col1, col2 = st.columns([1, 4])
                    col1.metric("시간", str(time_val))
                    with col2:
                        st.subheader(f"{title_val}")
                        st.write(f"📍 {addr_val}")
                        # 개별 내비는 가장 확실한 검색 연결
                        st.link_button(f"🚕 내비 연결", f"https://map.kakao.com/link/search/{urllib.parse.quote(addr_val)}", use_container_width=True)
                    st.divider()
            
            # --- 전체 경로 보기 (카카오맵 자동차 길찾기 공식 방식) ---
            if len(addr_list) >= 2:
                st.subheader("🗺️ 오늘의 전체 동선")
                
                # 출발지와 도착지를 설정하고, 중간 지점들은 경유지로 넣습니다.
                start_p = urllib.parse.quote(addr_list[0])
                end_p = urllib.parse.quote(addr_list[-1])
                
                # 카카오맵 웹 길찾기 URL (가장 표준적인 형식)
                # 이 방식은 주소가 2개 이상일 때 선이 그려질 확률이 가장 높습니다.
                route_url = f"https://map.kakao.com/link/from/{urllib.parse.quote(name_list[0])},{start_p}/to/{urllib.parse.quote(name_list[-1])},{end_p}"
                
                # 경유지가 1개 이상일 때만 추가
                if len(addr_list) > 2:
                    v_points = []
                    for i in range(1, len(addr_list)-1):
                        v_points.append(f"{urllib.parse.quote(name_list[i])},{urllib.parse.quote(addr_list[i])}")
                    route_url += "?via=" + "|".join(v_points)

                st.info("💡 아래 버튼을 누르면 전체 경로가 그려진 지도로 연결됩니다.")
                st.link_button(f"🚩 {selected_date} 전체 동선 선 연결 보기", route_url, use_container_width=True, type="primary")
                st.caption("※ 카카오맵 앱이 열리면 자동으로 경로가 계산됩니다.")
        else:
            st.warning("일정이 없습니다.")
except Exception as e:
    st.error("데이터 로딩 중...")
