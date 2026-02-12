import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# 1. 설정 정보
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbxCGd8QvYAquyvkgb9fmc57XnEdham1TgbHMRqzQVcFbKOYToPlrOGE8E8B8KFS74b3/exec"

KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")

@st.cache_data(ttl=3600)
def get_coords_cached(address):
    if not address or len(address) < 5: return None, None
    try:
        geolocator = Nominatim(user_agent="choi_camp_final_v4")
        location = geolocator.geocode(address, timeout=10)
        if location: return location.latitude, location.longitude
    except: return None, None
    return None, None

def update_sheet_status(row_idx, status_text):
    api_url = f"{script_url}?row={row_idx+1}&status={urllib.parse.quote(status_text)}"
    try:
        res = requests.get(api_url, timeout=15)
        if "성공" in res.text:
            st.toast(f"✅ {status_text} 처리 완료")
            return True
    except: st.error("📡 연결 실패")
    return False

st.markdown("""<style> div.stButton > button { width: 100% !important; height: 50px !important; } </style>""", unsafe_allow_html=True)
st.title("🚩 캠프 실시간 보고")

try:
    df = pd.read_csv(f"{sheet_url}&t={now_kst.timestamp()}")
    df = df.fillna("")
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    df['temp_time'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
    
    available_dates = sorted(df['날짜_dt'].unique())
    today_val = now_kst.date()
    default_idx = list(available_dates).index(today_val) if today_val in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    if st.button("🔄 페이지 새로고침"): st.rerun()
    st.divider()

    day_df = df[df['날짜_dt'] == selected_date].copy().reset_index()

    # --- [참석 완료 장소 기준 동선 정렬] ---
    # 1. '참석'이라고 표시된 행들만 필터링
    attended_events = day_df[day_df['참석여부'] == '참석'].sort_values('temp_time')
    
    base_point = None
    base_name = ""

    if not attended_events.empty:
        # 가장 최근에 '참석'을 누른 행사장 주소가 기준
        last_attended = attended_events.iloc[-1]
        base_point = get_coords_cached(last_attended['주소'])
        base_name = f"마지막 참석지: {last_attended['행사명']}"
    elif not day_df.empty:
        # 아직 아무것도 참석 안 했다면, 오늘의 첫 번째 일정을 기준점으로 설정
        first_event = day_df.sort_values('temp_time').iloc[0]
        base_point = get_coords_cached(first_event['주소'])
        base_name = f"오늘의 시작점: {first_event['행사명']}"

    # 아직 '참석/불참석' 결정 안 된 일정들
    future_events = day_df[day_df['참석여부'].isin(['', '미체크'])].copy()

    if base_point and base_point[0] and not future_events.empty:
        st.success(f"📍 기준 위치: **{base_name}**")
        
        def get_dist(addr):
            target = get_coords_cached(addr)
            return geodesic(base_point, target).meters if target and target[0] else 999999
        
        future_events['dist'] = future_events['주소'].apply(get_dist)
        # 시간순으로 먼저 정렬하고, 같은 시간대면 거리순(dist)으로 정렬
        sorted_future = future_events.sort_values(by=['temp_time', 'dist'])
        
        # 화면에 보여줄 데이터: 이미 처리된 것 + 앞으로 할 것(거리순)
        processed_events = day_df[~day_df['참석여부'].isin(['', '미체크'])].sort_values('temp_time')
        display_df = pd.concat([processed_events, sorted_future])
    else:
        display_df = day_df.sort_values('temp_time')

    # --- 출력 ---
    for _, row in display_df.iterrows():
        orig_idx = row['index']
        with st.container(border=True):
            status = str(row.get('참석여부', '')).strip()
            if status not in ["참석", "불참석"]: status = "미체크"
            
            title_tag = "✅" if status == "참석" else "❌" if status == "불참석" else "⏱️"
            st.markdown(f"### {title_tag} {row['시간']} | {row['행사명']}")
            st.caption(f"📍 {row['주소']}")
            
            if status == "미체크":
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🟢 참석", key=f"at_{orig_idx}"):
                        if update_sheet_status(orig_idx, "참석"): st.rerun()
                with c2:
                    if st.button("🔴 불참석", key=f"no_{orig_idx}"):
                        if update_sheet_status(orig_idx, "불참석"): st.rerun()
            else:
                if status == "참석": st.success(f"결과: {status}")
                else: st.error(f"결과: {status}")
                if st.button("🔄 수정하기", key=f"ed_{orig_idx}"):
                    if update_sheet_status(orig_idx, "미체크"): st.rerun()

            st.link_button("🚕 카카오내비 실행", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

except Exception as e:
    st.error(f"데이터 정렬 중... {e}")
