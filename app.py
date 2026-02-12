import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
import time

# 1. 설정 정보
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbzlPtAOqvz0wSgbspGz9PbZuDcdd-BBtbbep_uEtCFTaBd4vYG5Pu6jo0dkESkVBIgI/exec"

KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

st.set_page_config(page_title="최웅식 후보자님 동선", layout="centered")

def update_sheet_status(row_idx, status_text):
    api_url = f"{script_url}?row={row_idx}&status={urllib.parse.quote(status_text)}"
    try:
        res = requests.get(api_url, timeout=15)
        if "성공" in res.text:
            st.toast(f"✅ {status_text} 처리 완료")
            return True
    except: st.error("📡 시트 연결 실패")
    return False

# 2. 데이터 강제 로드 함수 (캐시 완전 차단)
def get_fresh_data(url):
    f_url = f"{url}&t={int(time.time())}"
    return pd.read_csv(f_url)

try:
    # 매번 앱을 실행할 때마다 새로운 데이터를 읽어옵니다.
    df = get_fresh_data(sheet_url)
    df = df.fillna("")
    
    if df.empty:
        st.error("⚠️ 시트에 데이터가 없습니다. 시트를 확인해주세요.")
        st.stop()

    # 날짜 처리
    df['날짜_str'] = df['날짜'].astype(str).str.strip()
    available_dates = sorted([d for d in df['날짜_str'].unique() if d and d != "nan"])
    
    if not available_dates:
        st.error("⚠️ 시트에서 '날짜' 데이터를 읽지 못했습니다.")
        st.stop()

    st.title("🚩 최웅식 후보자님 동선")
    
    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = 0
    for i, d in enumerate(available_dates):
        if today_str in d:
            default_idx = i
            break

    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    # 이 버튼을 누르면 무조건 시트의 최신 내용을 가져옵니다.
    if st.button("🔄 새로운 일정 불러오기"):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    day_df = df[df['날짜_str'] == selected_date].copy().reset_index()
    
    if day_df.empty:
        st.info(f"선택한 날짜({selected_date})에 일정이 없습니다.")
    else:
        # 데이터 타입 변환
        day_df['위도'] = pd.to_numeric(day_df['위도'], errors='coerce')
        day_df['경도'] = pd.to_numeric(day_df['경도'], errors='coerce')
        day_df['temp_time_dt'] = pd.to_datetime(day_df['시간'], errors='coerce')
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        # [정렬 로직]
        times = sorted(day_df['temp_time_dt'].dropna().unique())
        final_list = []
        last_ref = None
        
        # 마지막 참석지 기준
