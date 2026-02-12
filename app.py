import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time

# 1. 설정 및 한국 시간
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbxCGd8QvYAquyvkgb9fmc57XnEdham1TgbHMRqzQVcFbKOYToPlrOGE8E8B8KFS74b3/exec"
KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

st.set_page_config(page_title="최웅식 캠프 동선 가이드", layout="centered")

# 주소를 좌표로 바꾸는 함수 (무료 서비스 사용)
geolocator = Nominatim(user_agent="camp_app_v1")

def get_coords(address):
    try:
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
    except:
        return None, None
    return None, None

# CSS 설정
st.markdown("""<style> div.stButton > button { width: 100% !important; height: 50px !important; } </style>""", unsafe_allow_html=True)

st.title("🚩 캠프 동선 최적화 보고")

try:
    # 데이터 로드
    df = pd.read_csv(f"{sheet_url}&t={now_kst.timestamp()}")
    df = df.fillna("")
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    df['temp_time'] = pd.to_datetime(df['시간'], errors='coerce').dt.time

    # 날짜 선택 및 필터링
    available_dates = sorted(df['날짜_dt'].unique())
    today_val = now_kst.date()
    default_idx = list(available_dates).index(today_val) if today_val in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    if st.button("🔄 페이지 새로고침"): st.rerun()
    st.divider()

    day_df = df[df['날짜_dt'] == selected_date].copy()
    day_df = day_df.sort_values(by='temp_time')

    # --- 동선 정렬 로직 ---
    # 1. 현재 시간 기준으로 '지금' 혹은 '방금 끝난' 행사 찾기 (기준점)
    current_time = now_kst.time()
    past_events = day_df[day_df['temp_time'] <= current_time]
    
    base_coords = None
    if not past_events.empty:
        # 가장 최근에 있었던 행사의 주소를 기준점으로 잡음
        last_event_addr = past_events.iloc[-1]['주소']
        base_coords = get_coords(last_event_addr)

    # 2. 다음 시간대 행사들 거리 계산
    future_events = day_df[day_df['temp_time'] > current_time].copy()
    
    if base_coords[0] and not future_events.empty:
        st.info(f"📍 현재 위치 기준({past_events.iloc[-1]['시간']}) 가장 가까운 다음 동선을 추천합니다.")
        
        def calc_dist(addr):
            target_coords = get_coords(addr)
            if target_coords[0] and base_coords[0]:
                return geodesic(base_coords, target_coords).meters
            return 999999
        
        # 시간대가 같은 그룹끼리 거리순 정렬
        future_events['dist'] = future_events['주소'].apply(calc_dist)
        # 시간순으로 먼저 정렬하고, 같은 시간 안에서는 거리순(dist) 정렬
        day_df = pd.concat([past_events, future_events.sort_values(by=['temp_time', 'dist'])])
    else:
        day_df = day_df.sort_values(by='temp_time')

    # --- 리스트 출력 ---
    for idx, row in day_df.iterrows():
        with st.container(border=True):
            # 이미 지난 일정은 약간 흐리게 표시하거나 안내
            is_past = row['temp_time'] <= current_time
            title_prefix = "🏁 [종료] " if is_past else "⏱️ "
            
            st.markdown(f"### {title_prefix} {row['시간']} | {row['행사명']}")
            st.caption(f"📍 {row['주소']}")
            
            # 참석/불참/수정 로직 (기존과 동일)
            status = str(row.get('참석여부', '미체크')).strip()
            if status not in ["참석", "불참석"]: status = "미체크"
            
            if status == "미체크":
                if st.button("🟢 참석", key=f"at_{idx}"):
                    # (update_sheet_status 함수는 생략, 기존 함수 그대로 사용)
                    pass
                if st.button("🔴 불참석", key=f"no_{idx}"):
                    pass
            else:
                st.success(f"✅ {status}")

            st.link_button("🚕 카카오내비 실행", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

except Exception as e:
    st.error(f"데이터를 불러오는 중입니다... (주소 분석 중)")
