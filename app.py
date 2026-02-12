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
        geolocator = Nominatim(user_agent="choi_camp_v6")
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
st.title("🚩 캠프 실시간 동선 보고")

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

    day_df = df[df['날짜_dt'] == selected_date].copy().sort_values('temp_time')
    
    if not day_df.empty:
        # --- [참석 기반 계단식 정렬 로직] ---
        # 1. 마지막으로 '참석'한 행사가 있는지 확인
        attended_events = day_df[day_df['참석여부'] == '참석'].sort_values('temp_time')
        
        times = sorted(day_df['temp_time'].unique())
        final_list = []
        last_coords = None
        base_found = False

        # 만약 참석한 행사가 있다면 그곳을 강제 기준점으로 설정
        if not attended_events.empty:
            last_attended = attended_events.iloc[-1]
            last_coords = get_coords_cached(last_attended['주소'])
            base_found = True
            st.info(f"📍 실시간 기준: **{last_attended['행사명']}** (참석 위치)")

        for t in times:
            current_group = day_df[day_df['temp_time'] == t].copy()
            
            # 이미 처리된(참석/불참석) 그룹은 정렬하지 않고 그대로 유지
            if (current_group['참석여부'] != '미체크').any() and (current_group['참석여부'] != '').any():
                final_list.append(current_group.reset_index())
                # 만약 이 그룹에 마지막 참석지가 있었다면 이후 그룹은 이 좌표를 기준으로 정렬
                attended_in_group = current_group[current_group['참석여부'] == '참석']
                if not attended_in_group.empty:
                    last_coords = get_coords_cached(attended_in_group.iloc[-1]['주소'])
            else:
                # 미체크 그룹이고 기준점이 있다면 거리순 정렬
                if last_coords:
                    def calc_dist(addr):
                        target = get_coords_cached(addr)
                        return geodesic(last_coords, target).meters if target and target[0] else 999999
                    current_group['dist'] = current_group['주소'].apply(calc_dist)
                    current_group = current_group.sort_values('dist').reset_index()
                else:
                    # 기준점 없으면(오늘 첫 시작 전) 시간순 그대로
                    current_group = current_group.reset_index()
                
                final_list.append(current_group)
                # 다음 시간대를 위해 이 시간대의 1등을 기준점으로 갱신
                if not current_group.empty:
                    last_coords = get_coords_cached(current_group.iloc[0]['주소'])

        display_df = pd.concat(final_list)
        
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
                    st.success(f"결과: {status}")
                    if st.button("🔄 수정", key=f"ed_{orig_idx}"):
                        if update_sheet_status(orig_idx, "미체크"): st.rerun()

                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")
    else:
        st.warning("일정이 없습니다.")

except Exception as e:
    st.error(f"정렬 오류: {e}")
