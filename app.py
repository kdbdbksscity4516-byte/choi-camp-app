import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time

# 1. 설정 정보
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbxCGd8QvYAquyvkgb9fmc57XnEdham1TgbHMRqzQVcFbKOYToPlrOGE8E8B8KFS74b3/exec"

KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")

# --- 좌표 변환 함수 (로그 강화) ---
@st.cache_data(ttl=3600)
def get_coords_cached(address):
    if not address or len(address) < 2: return None
    try:
        # 서비스 이름을 매번 조금씩 바꿔서 차단을 피함
        geolocator = Nominatim(user_agent=f"choi_agent_{int(time.time())}")
        location = geolocator.geocode(address, timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except Exception as e:
        return None
    return None

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
st.title("🚩 캠프 실시간 동선 보고")

try:
    # 데이터 로드
    df = pd.read_csv(f"{sheet_url}&t={now_kst.timestamp()}")
    df = df.fillna("")
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    df['temp_time'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
    
    available_dates = sorted(df['날짜_dt'].unique())
    today_val = now_kst.date()
    default_idx = list(available_dates).index(today_val) if today_val in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    if st.button("🔄 페이지 새로고침"):
        st.cache_data.clear() # 캐시까지 싹 지우고 새로고침
        st.rerun()
    st.divider()

    day_df = df[df['날짜_dt'] == selected_date].copy().reset_index()
    
    if not day_df.empty:
        # --- [거리 정렬 핵심 엔진] ---
        times = sorted(day_df['temp_time'].unique())
        final_rows = []
        
        # 1. 기준점 찾기 (마지막 참석지 혹은 첫 일정)
        attended = day_df[day_df['참석여부'] == '참석'].sort_values('temp_time')
        current_base_coords = None
        
        if not attended.empty:
            last_addr = attended.iloc[-1]['주소']
            current_base_coords = get_coords_cached(last_addr)
            st.info(f"📍 기준점: {attended.iloc[-1]['행사명']} (참석 완료 지점)")
        else:
            first_event = day_df.sort_values('temp_time').iloc[0]
            current_base_coords = get_coords_cached(first_event['주소'])
            st.info(f"📍 기준점: {first_event['행사명']} (오늘의 첫 일정)")

        # 2. 시간대별 계단식 정렬
        for t in times:
            group = day_df[day_df['temp_time'] == t].copy()
            
            # 이미 결과가 나온 것은 정렬 건너뜀
            if (group['참석여부'].str.strip() != "").any() and (group['참석여부'].str.strip() != "미체크").any():
                final_rows.append(group)
                # 이 그룹에 참석이 있다면 기준점 업데이트
                att_in_group = group[group['참석여부'] == '참석']
                if not att_in_group.empty:
                    new_coords = get_coords_cached(att_in_group.iloc[-1]['주소'])
                    if new_coords: current_base_coords = new_coords
            else:
                # 미체크 일정들은 거리순 정렬
                if current_base_coords:
                    def get_d(addr):
                        target = get_coords_cached(addr)
                        if target:
                            return geodesic(current_base_coords, target).meters
                        return 999999
                    group['dist'] = group['주소'].apply(get_d)
                    group = group.sort_values('dist')
                
                final_rows.append(group)
                # 다음 시간대를 위해 이 시간대 1등을 기준점으로 갱신
                if not group.empty:
                    new_coords = get_coords_cached(group.iloc[0]['주소'])
                    if new_coords: current_base_coords = new_coords

        display_df = pd.concat(final_rows)

        # --- 출력 부분 ---
        for _, row in display_df.iterrows():
            orig_idx = row['index']
            with st.container(border=True):
                status = str(row.get('참석여부', '')).strip()
                if status not in ["참석", "불참석"]: status = "미체크"
                
                st.markdown(f"### {'✅' if status=='참석' else '❌' if status=='불참석' else '⏱️'} {row['시간']} | {row['행사명']}")
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
                    st.success(f"결과: {status}")
                    if st.button("🔄 수정", key=f"ed_{orig_idx}"):
                        if update_sheet_status(orig_idx, "미체크"): st.rerun()

                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")
    else:
        st.warning("표시할 일정이 없습니다.")

except Exception as e:
    st.error(f"⚠️ 시스템 오류: {e}")
