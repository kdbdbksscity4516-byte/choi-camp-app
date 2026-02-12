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

# [핵심] 앱이 꺼지기 전까지 마지막 클릭 좌표를 기억하는 메모리 공간
if 'last_lat' not in st.session_state:
    st.session_state.last_lat = None
if 'last_lon' not in st.session_state:
    st.session_state.last_lon = None

def update_sheet_status(row_idx, status_text):
    api_url = f"{script_url}?row={row_idx}&status={urllib.parse.quote(status_text)}"
    try:
        res = requests.get(api_url, timeout=10)
        return "성공" in res.text
    except: return False

try:
    # 데이터 로드 (캐시 무력화)
    df = pd.read_csv(f"{sheet_url}&t={int(time.time())}")
    df = df.fillna("")
    df.loc[df['참석여부'] == "", '참석여부'] = "미체크"
    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    df['날짜_str'] = df['날짜'].astype(str).str.strip()

    st.title("🚩 최웅식 후보자님 실시간 동선")

    # 날짜 선택
    available_dates = sorted([d for d in df['날짜_str'].unique() if d and d != "nan"])
    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = available_dates.index(today_str) if today_str in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)

    day_df = df[df['날짜_str'] == selected_date].copy().reset_index()

    if not day_df.empty:
        day_df['temp_time_dt'] = pd.to_datetime(day_df['시간'], errors='coerce')
        
        # [로직 변경] 메모리에 저장된 좌표를 최우선 기준점으로 사용
        current_anchor = None
        if st.session_state.last_lat and st.session_state.last_lon:
            current_anchor = (st.session_state.last_lat, st.session_state.last_lon)
        
        # 시간대별 정렬
        times = sorted(day_df['temp_time_dt'].dropna().unique())
        final_list = []

        for t in times:
            group = day_df[day_df['temp_time_dt'] == t].copy()
            group_att = group[group['참석여부'] == '참석']
            group_pending = group[group['참석여부'] == '미체크'].copy()
            
            # 기준점(전주)이 있다면 미체크 항목들을 그 거리순으로 정렬
            if not group_pending.empty and current_anchor:
                group_pending['dist'] = group_pending.apply(
                    lambda r: geodesic(current_anchor, (r['위도'], r['경도'])).meters if not pd.isna(r['위도']) else 999999, axis=1
                )
                group_pending = group_pending.sort_values('dist')
            
            group_no = group[group['참석여부'] == '불참석']
            final_list.append(pd.concat([group_att, group_pending, group_no]))

        display_df = pd.concat(final_list)

        # 지도 및 리스트 출력
        m_df = display_df[display_df['참석여부'] != '불참석']
        m_df = m_df[m_df['위도'].notna() & m_df['경도'].notna()]
        if not m_df.empty:
            m = folium.Map(location=[m_df.iloc[0]['위도'], m_df.iloc[0]['경도']], zoom_start=11)
            for _, r in m_df.iterrows():
                folium.Marker([r['위도'], r['경도']], popup=r['행사명'], icon=folium.Icon(color='blue' if r['참석여부']=='참석' else 'red')).add_to(m)
            folium_static(m)

        for _, row in display_df.iterrows():
            orig_idx = row['index']
            with st.container(border=True):
                st.markdown(f"### {row['시간']} | {row['행사명']}")
                st.caption(f"📍 {row['주소']}")
                
                if row['참석여부'] == "미체크":
                    c1, c2 = st.columns(2)
                    if c1.button("🟢 참석", key=f"at_{orig_idx}"):
                        # 1. 시트 업데이트 요청
                        update_sheet_status(orig_idx, "참석")
                        # 2. [가장 중요] 클릭한 장소의 좌표를 메모리에 박제
                        st.session_state.last_lat = row['위도']
                        st.session_state.last_lon = row['경도']
                        st.cache_data.clear()
                        st.rerun()
                    if c2.button("🔴 불참석", key=f"no_{orig_idx}"):
                        update_sheet_status(orig_idx, "불참석")
                        st.rerun()
                else:
                    st.success(f"결과: {row['참석여부']}")
                    if st.button("🔄 재선택", key=f"re_{orig_idx}"):
                        update_sheet_status(orig_idx, "미체크")
                        st.rerun()
                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

except Exception as e:
    st.error(f"오류 발생: {e}")
