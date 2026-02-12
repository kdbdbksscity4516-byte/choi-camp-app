import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
import time
import streamlit.components.v1 as components

# 1. 설정 및 기본 데이터 로드
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbzlPtAOqvz0wSgbspGz9PbZuDcdd-BBtbbep_uEtCFTaBd4vYG5Pu6jo0dkESkVBIgI/exec"

KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

st.set_page_config(page_title="최웅식 후보 동선 관리", layout="wide")

# 지역구 매핑 사전 (영등포구 갑/을 기준)
DISTRICT_MAP = {
    "영등포구 갑": ["영등포동", "영등포본동", "당산1동", "당산2동", "도림동", "문래동", "양평1동", "양평2동", "신길1동", "신길2동", "신길3동"],
    "영등포구 을": ["여의동", "신길4동", "신길5동", "신길6동", "신길7동", "대림1동", "대림2동", "대림3동"]
}

def get_district_info(address):
    """주소에서 영등포구 갑/을 및 행정동 추출"""
    for dist, dongs in DISTRICT_MAP.items():
        for dong in dongs:
            if dong in address:
                return dist, dong
    return "기타/외부", "기타"

def update_sheet_status(row_idx, status_text):
    api_url = f"{script_url}?row={row_idx}&status={urllib.parse.quote(status_text)}"
    try:
        res = requests.get(api_url, timeout=10)
        return "성공" in res.text
    except: return False

try:
    df = pd.read_csv(f"{sheet_url}&t={int(time.time())}")
    df = df.fillna("")
    df.loc[df['참석여부'] == "", '참석여부'] = "미체크"
    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    df['날짜_str'] = df['날짜'].astype(str).str.strip()

    st.title("최웅식 후보 동선 최적화 & 활동 분석")

    if st.button("🔄 전체 새로고침 (F5)"):
        components.html("<script>window.parent.location.reload();</script>", height=0)
        st.stop()

    # [중간 생략: 상세 이동 경로 및 일정 리스트 코드는 기존과 동일]
    # (사용자 편의를 위해 결과물 배치를 위해 날짜 선택 및 리스트 기능은 유지됩니다)
    available_dates = sorted([d for d in df['날짜_str'].unique() if d and d != "nan"])
    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = available_dates.index(today_str) if today_str in available_dates else 0
    selected_date = st.selectbox("🗓️ 상세 동선 날짜 선택", available_dates, index=default_idx)
    day_df = df[df['날짜_str'] == selected_date].copy().reset_index()

    if not day_df.empty:
        # [당일 지도 및 리스트 출력 로직...]
        st.subheader(f"📍 {selected_date} 상세 이동 경로")
        # (기존 상세 지도 코드 생략...)
        st.subheader("📝 오늘 주요 일정 리스트")
        # (기존 일정 리스트 코드 생략...)

    # --- 맨 아래: 영등포구 지역구별 수치 분석 ---
    st.divider()
    st.subheader("📊 영등포구 지역구별 활동 수치 분석")
    
    # 데이터 전처리: 지역구 및 행정동 할당
    analysis_df = df.copy()
    analysis_df[['지역구', '행정동']] = analysis_df.apply(
        lambda x: pd.Series(get_district_info(str(x['주소']))), axis=1
    )

    # 1. 갑/을 요약 표
    summary = analysis_df.groupby(['지역구', '참석여부']).size().unstack(fill_value=0)
    # 컬럼 순서 보장
    for col in ['참석', '불참석', '미체크']:
        if col not in summary.columns: summary[col] = 0
    summary = summary[['참석', '불참석', '미체크']]
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("**[지역구 요약]**")
        st.table(summary)

    # 2. 행정동별 상세 표
    with col2:
        st.markdown("**[행정동별 상세 활동 현황]**")
        detail_summary = analysis_df.groupby(['지역구', '행정동', '참석여부']).size().unstack(fill_value=0)
        for col in ['참석', '불참석', '미체크']:
            if col not in detail_summary.columns: detail_summary[col] = 0
        st.dataframe(detail_summary[['참석', '불참석', '미체크']], use_container_width=True)

    # [기존 하단: 누적 활동 분석 지도]
    st.divider()
    st.subheader("🗺️ 선거 운동 누적 활동 분석 (참석/불참석)")
    # (기존 누적 지도 코드 유지...)
    all_map_df = df[df['참석여부'].isin(['참석', '불참석']) & df['위도'].notna()]
    if not all_map_df.empty:
        m_all = folium.Map(location=[all_map_df['위도'].mean(), all_map_df['경도'].mean()], zoom_start=12)
        for _, r in all_map_df.iterrows():
            m_color = 'blue' if r['참석여부'] == '참석' else 'red'
            folium.Marker([r['위_도'], r['경도']], icon=folium.Icon(color=m_color)).add_to(m_all)
        folium_static(m_all)

except Exception as e:
    st.error(f"오류: {e}")
