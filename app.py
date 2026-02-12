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

# --- 주소 인식 강화 함수 ---
@st.cache_data(ttl=3600)
def get_coords_v9(address):
    if not address: return None
    # 검색어 정제: '서울시' -> '서울특별시' 등으로 보정 시도
    clean_addr = str(address).replace("서울시", "서울특별시").strip()
    
    try:
        # User-Agent를 매번 다르게 해서 차단 회피
        ua = f"camp_app_{int(time.time())}"
        geolocator = Nominatim(user_agent=ua)
        
        # 1차 시도
        location = geolocator.geocode(clean_addr, timeout=10)
        if location: return (location.latitude, location.longitude)
        
        # 2차 시도 (주소를 뒤에서부터 조금씩 잘라서 검색 - 예: '당산로 123'만 검색)
        short_addr = " ".join(clean_addr.split()[-2:])
        location = geolocator.geocode(short_addr, timeout=10)
        if location: return (location.latitude, location.longitude)
        
    except:
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
    df = pd.read_csv(f"{sheet_url}&t={now_kst.timestamp()}")
    df = df.fillna("")
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    df['temp_time'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
    
    available_dates = sorted(df['날짜_dt'].unique())
    today_val = now_kst.date()
    default_idx = list(available_dates).index(today_val) if today_val in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    if st.button("🔄 전체 데이터 및 동선 다시 읽기"):
        st.cache_data.clear()
        st.rerun()
    st.divider()

    day_df = df[df['날짜_dt'] == selected_date].copy().reset_index()
    
    if not day_df.empty:
        # 1. 기준 좌표 찾기
        attended = day_df[day_df['참석여부'] == '참석'].sort_values('temp_time')
        base_coords = None
        
        if not attended.empty:
            base_coords = get_coords_v9(attended.iloc[-1]['주소'])
            st.info(f"📍 기준: {attended.iloc[-1]['행사명']} (참석지)")
        else:
            first_event = day_df.sort_values('temp_time').iloc[0]
            base_coords = get_coords_v9(first_event['주소'])
            st.info(f"📍 기준: {first_event['행사명']} (첫 일정)")

        # 2. 거리 계산 및 정렬
        times = sorted(day_df['temp_time'].unique())
        final_list = []
        last_ref = base_coords

        for t in times:
            group = day_df[day_df['temp_time'] == t].copy()
            # 미체크 일정 정렬
            if not (group['참석여부'].isin(['참석', '불참석'])).any() and last_ref:
                group['dist'] = group['주소'].apply(lambda x: geodesic(last_ref, get_coords_v9(x)).meters if get_coords_v9(x) else 999999)
                group = group.sort_values('dist')
            
            final_list.append(group)
            # 기준점 갱신
            if not group.empty:
                top_coords = get_coords_v9(group.iloc[0]['주소'])
                if top_coords: last_ref = top_coords

        display_df = pd.concat(final_list)

        # 3. 출력
        for _, row in display_df.iterrows():
            orig_idx = row['index']
            with st.container(border=True):
                status = str(row.get('참석여부', '')).strip()
                if status not in ["참석", "불참석"]: status = "미체크"
                st.markdown(f"### {row['시간']} | {row['행사명']}")
                st.caption(f"📍 {row['주소']}")
                
                # 정렬 작동 여부 확인용 (실제 거리 표시)
                coords = get_coords_v9(row['주소'])
                if coords:
                    st.caption(f"✅ 위치 인식됨")
                else:
                    st.caption(f"⚠️ 위치 인식 안 됨 (주소를 다시 확인해 주세요)")

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
        st.warning("데이터가 없습니다.")

except Exception as e:
    st.error(f"오류: {e}")
