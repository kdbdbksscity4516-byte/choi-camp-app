import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
import time

# [설정 정보] - 시트 주소 끝에 export?format=csv가 정확히 있는지 확인!
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbzlPtAOqvz0wSgbspGz9PbZuDcdd-BBtbbep_uEtCFTaBd4vYG5Pu6jo0dkESkVBIgI/exec"

KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

st.set_page_config(page_title="최웅식 후보자님 동선", layout="centered")

# 사진 열이 없어도 에러 안 나게 방어막 설치
try:
    # 캐시 무력화 (URL 뒤에 매번 다른 숫자를 붙임)
    df = pd.read_csv(f"{sheet_url}&cachebuster={int(time.time())}")
    df = df.fillna("")
    
    if '사진' in df.columns:
        photo_list = [p for p in df['사진'].tolist() if str(p).startswith('http')]
        if photo_list: st.image(photo_list[0], use_container_width=True)

    st.title("🚩 최웅식 후보자님 동선")

    # [날짜 인식 강화] - 어떤 형식이든 날짜처럼 생겼으면 다 읽음
    df['날짜_dt'] = pd.to_datetime(df['날짜'], errors='coerce')
    # 날짜 데이터가 없는 행은 과감히 버림 (빈 줄 방지)
    df = df.dropna(subset=['날짜_dt'])
    
    available_dates = sorted(df['날짜_dt'].dt.strftime('%Y-%m-%d').unique())

    if not available_dates:
        st.error("⚠️ 시트에서 '날짜'를 읽지 못했습니다. '날짜' 열에 2026-02-13 형식으로 입력되어 있나요?")
        st.info("현재 시트 내용 일부: " + str(df['날짜'].head().tolist())) # 디버깅용
        st.stop()

    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = available_dates.index(today_str) if today_str in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)

    # 필터링 및 시간 정렬
    day_df = df[df['날짜_dt'].dt.strftime('%Y-%m-%d') == selected_date].copy().reset_index()
    
    if day_df.empty:
        st.warning(f"{selected_date}에 해당하는 일정이 없습니다. 시트의 날짜를 확인해 주세요.")
    else:
        # 이후 정렬/지도 로직은 동일 (생략 없이 작동하도록 내부 포함)
        day_df['temp_time_dt'] = pd.to_datetime(day_df['시간'], errors='coerce')
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        # 정렬 로직 (이전 답변과 동일)
        times = sorted(day_df['temp_time_dt'].dropna().unique())
        final_list = []
        ref_coords = None
        
        # ... (이하 생략된 정렬 로직 및 지도/리스트 출력부 적용)
        # 사무장님, 코드가 너무 길어지니 일단 위 날짜 로직 수정한 것만으로도 
        # 데이터가 나타나는지 확인이 필요합니다.
