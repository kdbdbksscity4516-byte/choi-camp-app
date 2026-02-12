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
                        # 개별 내비는 가장 안전한 검색 링크 사용
                        st.link_button(f"🚕 내비 연결", f"https://map.kakao.com/link/search/{urllib.parse.quote(addr_val)}", use_container_width=True)
                    st.divider()
            
            # --- 전체 경로 보기 (카카오맵 공식 길찾기 파라미터 적용) ---
            if len(addr_list) >= 2:
                # 1. 기본 경로 (출발지/목적지)
                start_name = urllib.parse.quote(name_list[0])
                start_addr = urllib.parse.quote(addr_list[0])
                end_name = urllib.parse.quote(name_list[-1])
                end_addr = urllib.parse.quote(addr_list[-1])
                
                # 카카오맵 공식 길찾기 웹 주소 (파라미터 구분 정확히 수정)
                base_url = f"https://map.kakao.com/link/from/{start_name},{start_addr}/to/{end_name},{end_addr}"
                
                # 2. 경유지가 있다면 ?via= 대신 &via= 를 사용해야 합니다 (이미 /from/to/ 경로가 있으므로)
                if len(addr_list) > 2:
                    v_points = []
                    for i in range(1, len(addr_list)-1):
                        v_points.append(f"{urllib.parse.quote(name_list[i])},{urllib.parse.quote(addr_list[i])}")
                    # 최종 URL 조립
                    final_route_url = f"{base_url}?via={'|'.join(v_points)}"
                else:
                    final_route_url = base_url

                st.success("✅ 전체 동선 지도가 준비되었습니다.")
                st.link_button(f"🗺️ {selected_date} 전체 경로 선 연결 보기", final_route_url, use_container_width=True, type="primary")
                st.caption("※ 버튼을 누르면 카카오맵 앱에서 경로가 자동으로 계산됩니다.")
        else:
            st.warning("일정이 없습니다.")
except Exception as e:
    st.error(f"데이터 로딩 중 오류: {e}")
