import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# 1. 설정 정보 (사무장님의 기존 URL)
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbxCGd8QvYAquyvkgb9fmc57XnEdham1TgbHMRqzQVcFbKOYToPlrOGE8E8B8KFS74b3/exec"

# 한국 시간 설정
KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")

# --- 좌표 변환 캐시 (속도 향상) ---
@st.cache_data(ttl=3600)
def get_coords_cached(address):
    if not address or len(address) < 5: return None, None
    try:
        geolocator = Nominatim(user_agent="choi_camp_v3")
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude
    except:
        return None, None
    return None, None

# 시트 기록 함수 (참석/불참석용)
def update_sheet_status(row_idx, status_text):
    api_url = f"{script_url}?row={row_idx+1}&status={urllib.parse.quote(status_text)}"
    try:
        res = requests.get(api_url, timeout=15)
        if "성공" in res.text:
            st.toast(f"✅ {status_text} 처리되었습니다.")
            return True
    except:
        st.error("📡 연결 실패")
    return False

# CSS: 버튼 가로 꽉 차게
st.markdown("""<style> div.stButton > button { width: 100% !important; height: 50px !important; margin-bottom: 5px !important; } </style>""", unsafe_allow_html=True)

st.title("🚩 캠프 실시간 보고")

try:
    df = pd.read_csv(f"{sheet_url}&t={now_kst.timestamp()}")
    df = df.fillna("")
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    df['temp_time'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
    
    # 0. 날짜 선택
    available_dates = sorted(df['날짜_dt'].unique())
    today_val = now_kst.date()
    default_idx = list(available_dates).index(today_val) if today_val in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    # 1. 페이지 새로고침 버튼
    if st.button("🔄 페이지 새로고침"): st.rerun()
    st.divider()

    day_df = df[df['날짜_dt'] == selected_date].copy().reset_index()

    # --- 동선 최적화 계산 ---
    current_time = now_kst.time()
    past_events = day_df[day_df['temp_time'] <= current_time]
    future_events = day_df[day_df['temp_time'] > current_time].copy()

    if not past_events.empty and not future_events.empty:
        last_event = past_events.iloc[-1]
        lat, lon = get_coords_cached(last_event['주소'])
        
        if lat:
            st.info(f"📍 현재 '{last_event['행사명']}' 위치 기준 가장 가까운 다음 동선 추천")
            base_point = (lat, lon)
            future_events['dist'] = future_events.apply(lambda r: geodesic(base_point, get_coords_cached(r['주소'])).meters if get_coords_cached(r['주소'])[0] else 999999, axis=1)
            future_events = future_events.sort_values(by=['temp_time', 'dist'])
            display_df = pd.concat([past_events, future_events])
        else:
            display_df = day_df.sort_values(by='temp_time')
    else:
        display_df = day_df.sort_values(by='temp_time')

    # --- 일정 출력 (버튼 복구) ---
    for _, row in display_df.iterrows():
        orig_idx = row['index'] # 원본 시트의 행 번호
        with st.container(border=True):
            is_past = row['temp_time'] <= current_time
            title_tag = "🏁 [종료]" if is_past else "⏱️"
            st.markdown(f"### {title_tag} {row['시간']} | {row['행사명']}")
            st.caption(f"📍 {row['주소']}")
            
            # 참석 여부 로직
            status = str(row.get('참석여부', '미체크')).strip()
            if status not in ["참석", "불참석"]: status = "미체크"

            if status == "미체크":
                if st.button("🟢 참석", key=f"at_{orig_idx}"):
                    if update_sheet_status(orig_idx, "참석"): st.rerun()
                if st.button("🔴 불참석", key=f"no_{orig_idx}"):
                    if update_sheet_status(orig_idx, "불참석"): st.rerun()
            else:
                if status == "참석": st.success(f"✅ {status}")
                else: st.error(f"✅ {status}")
                if st.button("🔄 수정하기", key=f"ed_{orig_idx}"):
                    if update_sheet_status(orig_idx, "미체크"): st.rerun()

            st.link_button("🚕 카카오내비 실행", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

except Exception as e:
    st.error(f"데이터 로딩 중... {e}")
