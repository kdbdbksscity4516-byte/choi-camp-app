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

# --- 좌표 변환 함수 (성능 개선 및 오류 로그 추가) ---
@st.cache_data(ttl=600) # 10분만 기억
def get_coords_final(address):
    if not address or len(str(address)) < 5: return None
    try:
        # Nominatim 서비스는 한국 주소 인식이 불안정할 수 있어 여러 번 시도
        geolocator = Nominatim(user_agent="choi_camp_v8")
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
    df = pd.read_csv(f"{sheet_url}&t={now_kst.timestamp()}")
    df = df.fillna("")
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    df['temp_time'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
    
    available_dates = sorted(df['날짜_dt'].unique())
    today_val = now_kst.date()
    default_idx = list(available_dates).index(today_val) if today_val in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    if st.button("🔄 거리 다시 계산하기 (새로고침)"):
        st.cache_data.clear()
        st.rerun()
    st.divider()

    day_df = df[df['날짜_dt'] == selected_date].copy().reset_index()
    
    if not day_df.empty:
        # --- [거리 정렬 핵심 엔진] ---
        # 1. 기준점 잡기 (마지막 참석 혹은 첫 일정)
        attended = day_df[day_df['참석여부'] == '참석'].sort_values('temp_time')
        base_coords = None
        base_name = ""

        if not attended.empty:
            last_target = attended.iloc[-1]
            base_coords = get_coords_final(last_target['주소'])
            base_name = last_target['행사명']
        else:
            first_target = day_df.sort_values('temp_time').iloc[0]
            base_coords = get_coords_final(first_target['주소'])
            base_name = first_target['행사명']

        # 기준점이 좌표를 못 찾으면 경고 띄우기
        if not base_coords:
            st.error(f"❌ 기준점 '{base_name}'의 주소를 인식하지 못했습니다. 주소를 더 정확하게 써주세요.")
        else:
            st.success(f"📍 기준점 인식 성공: **{base_name}**")

        # 2. 계단식 정렬
        times = sorted(day_df['temp_time'].unique())
        final_rows = []
        last_ref_coords = base_coords

        for t in times:
            group = day_df[day_df['temp_time'] == t].copy()
            
            # 이미 처리된 일정(참석/불참석)은 정렬 없이 추가
            if (group['참석여부'].isin(['참석', '불참석'])).any():
                final_rows.append(group)
                # 만약 참석이 있으면 그 다음 정렬을 위해 기준점 업데이트
                att_row = group[group['참석여부'] == '참석']
                if not att_row.empty:
                    new_c = get_coords_final(att_row.iloc[-1]['주소'])
                    if new_c: last_ref_coords = new_c
            else:
                # 미체크 일정은 거리 계산 정렬
                if last_ref_coords:
                    def calc_dist(addr):
                        target = get_coords_final(addr)
                        if target: return geodesic(last_ref_coords, target).meters
                        return 99999999 # 주소 못 찾으면 맨 뒤로
                    
                    group['dist'] = group['주소'].apply(calc_dist)
                    group = group.sort_values('dist')
                
                final_rows.append(group)
                # 다음 시간대를 위해 이 시간대 1순위로 기준점 갱신
                if not group.empty:
                    new_c = get_coords_final(group.iloc[0]['주소'])
                    if new_c: last_ref_coords = new_c

        display_df = pd.concat(final_rows)

        # --- 출력 ---
        for _, row in display_df.iterrows():
            orig_idx = row['index']
            with st.container(border=True):
                status = str(row.get('참석여부', '')).strip()
                if status not in ["참석", "불참석"]: status = "미체크"
                
                st.markdown(f"### {'✅' if status=='참석' else '❌' if status=='불참석' else '⏱️'} {row['시간']} | {row['행사명']}")
                st.caption(f"📍 {row['주소']}")
                
                # 거리 계산이 됐는지 확인용 (사무장님 확인용 숨김 캡션)
                if 'dist' in row and row['dist'] < 99999999:
                    st.caption(f"📏 예상 거리: {round(row['dist']/1000, 1)}km")

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
except Exception as e:
    st.error(f"오류: {e}")
