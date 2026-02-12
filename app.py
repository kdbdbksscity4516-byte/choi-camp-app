import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# 1. 설정 및 한국 시간
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbxCGd8QvYAquyvkgb9fmc57XnEdham1TgbHMRqzQVcFbKOYToPlrOGE8E8B8KFS74b3/exec"
KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

st.set_page_config(page_title="최웅식 캠프 동선 가이드", layout="centered")

# --- 좌표 변환 캐시 설정 (한 번 찾은 주소는 다시 안 찾음) ---
@st.cache_data(ttl=3600) # 1시간 동안 좌표 기억
def get_coords_cached(address):
    if not address or len(address) < 5: return None, None
    try:
        geolocator = Nominatim(user_agent="choi_camp_v2")
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude
    except:
        return None, None
    return None, None

# CSS
st.markdown("""<style> div.stButton > button { width: 100% !important; height: 50px !important; } </style>""", unsafe_allow_html=True)

st.title("🚩 캠프 실시간 동선")

try:
    # 데이터 로드
    df = pd.read_csv(f"{sheet_url}&t={now_kst.timestamp()}")
    df = df.fillna("")
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    df['temp_time'] = pd.to_datetime(df['시간'], errors='coerce').dt.time

    # 날짜 선택
    available_dates = sorted(df['날짜_dt'].unique())
    today_val = now_kst.date()
    default_idx = list(available_dates).index(today_val) if today_val in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    if st.button("🔄 페이지 새로고침"): st.rerun()
    st.divider()

    day_df = df[df['날짜_dt'] == selected_date].copy()
    day_df = day_df.sort_values(by='temp_time')

    # --- 동선 최적화 계산 ---
    current_time = now_kst.time()
    past_events = day_df[day_df['temp_time'] <= current_time]
    future_events = day_df[day_df['temp_time'] > current_time].copy()

    if not past_events.empty and not future_events.empty:
        # 마지막 장소 기준점 잡기
        last_addr = past_events.iloc[-1]['주소']
        lat, lon = get_coords_cached(last_addr)
        
        if lat:
            st.info(f"📍 현재 '{past_events.iloc[-1]['행사명']}' 위치 기준으로 가장 가까운 다음 행사를 정렬합니다.")
            base_point = (lat, lon)
            
            def add_dist(row):
                t_lat, t_lon = get_coords_cached(row['주소'])
                if t_lat:
                    return geodesic(base_point, (t_lat, t_lon)).meters
                return 999999

            future_events['dist'] = future_events.apply(add_dist, axis=1)
            # 같은 시간대 안에서만 거리순 정렬
            future_events = future_events.sort_values(by=['temp_time', 'dist'])
            day_df = pd.concat([past_events, future_events])
        else:
            st.warning("⚠️ 현재 위치의 좌표를 분석할 수 없어 시간순으로 표시합니다.")
    
    # --- 출력 부분 ---
    for idx, row in day_df.iterrows():
        with st.container(border=True):
            is_past = row['temp_time'] <= current_time
            title_tag = "🏁 [종료]" if is_past else "⏱️"
            
            st.markdown(f"### {title_tag} {row['시간']} | {row['행사명']}")
            st.caption(f"📍 {row['주소']}")
            
            # (이하 참석/불참 및 내비 버튼 로직 동일하게 유지)
            st.link_button("🚕 카카오내비 실행", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

except Exception as e:
    st.error("데이터를 불러오는 중입니다. 잠시 후 다시 시도해 주세요.")
