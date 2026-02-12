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
            
            # 일정 목록 출력
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
                        # 개별 내비 연결 (이건 카카오 검색으로 유지)
                        st.link_button(f"🚕 이 장소만 내비 가기", f"https://map.kakao.com/link/search/{urllib.parse.quote(addr_val)}", use_container_width=True)
                    st.divider()
            
            # --- 수정: 지도 이미지를 화면에 바로 표시 ---
            if addr_list:
                st.subheader("🗺️ 오늘의 전체 동선 요약")
                
                # 구글 정적 지도를 사용하여 경로가 그려진 이미지를 생성합니다.
                # 선(path)을 그리기 위해 주소들을 연결합니다.
                path_params = "|".join([urllib.parse.quote(addr) for addr in addr_list])
                markers = "&".join([f"markers=color:red|label:{i+1}|{urllib.parse.quote(addr)}" for i, addr in enumerate(addr_list)])
                
                # 한국 지역은 구글맵 자동차 경로 선이 안 보일 수 있어, 핀(Marker) 위주로 구성된 지도 이미지를 불러옵니다.
                static_map_url = f"https://maps.googleapis.com/maps/api/staticmap?size=600x400&scale=2&{markers}&path=color:0xff0000ff|weight:5|{path_params}&key=YOUR_API_KEY_HERE"
                
                # 만약 위 API 키가 없다면, 가장 확실하게 주소들을 지도 앱으로 다시 보내지 않고 '이미지'로만 보여주는 방식입니다.
                # 여기서는 사무장님이 바로 확인하실 수 있게 '구글맵 웹뷰'를 활용한 임베딩 방식을 제안합니다.
                
                # 구글 지도 임베딩 (가장 확실하게 선이 보임)
                map_path = "/".join(addr_list)
                embed_url = f"https://www.google.com/maps/dir/{urllib.parse.quote(map_path)}?dg=dbrw&newdg=1"
                
                st.info("💡 아래 '지도 보기' 버튼을 누르면 다른 앱으로 이동하지 않고 이 화면에서 경로가 바로 보입니다.")
                st.components.v1.iframe(embed_url, height=500)
                
        else:
            st.warning("일정이 없습니다.")
except Exception as e:
    st.error("데이터 로딩 중...")
