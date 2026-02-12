import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
import time

# 1. 설정 및 세션 상태 초기화
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbzlPtAOqvz0wSgbspGz9PbZuDcdd-BBtbbep_uEtCFTaBd4vYG5Pu6jo0dkESkVBIgI/exec"

KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

st.set_page_config(page_title="최웅식 후보자님 동선", layout="centered")

if 'last_lat' not in st.session_state: st.session_state.last_lat = None
if 'last_lon' not in st.session_state: st.session_state.last_lon = None

def update_sheet_status(row_idx, status_text):
    api_url = f"{script_url}?row={row_idx}&status={urllib.parse.quote(status_text)}"
    try:
        res = requests.get(api_url, timeout=10)
        return "성공" in res.text
    except: return False

try:
    # 2. 데이터 로드 (캐시 무력화)
    df = pd.read_csv(f"{sheet_url}&t={int(time.time())}")
    df = df.fillna("")
    df.loc[df['참석여부'] == "", '참석여부'] = "미체크"
    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    df['날짜_str'] = df['날짜'].astype(str).str.strip()

    st.title("🚩 최웅식 후보자님 실시간 동선")

    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

    available_dates = sorted([d for d in df['날짜_str'].unique() if d and d != "nan"])
    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = available_dates.index(today_str) if today_str in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)

    day_df = df[df['날짜_str'] == selected_date].copy().reset_index()

    if not day_df.empty:
        day_df['temp_time_dt'] = pd.to_datetime(day_df['시간'], errors='coerce')
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        # 기준점 설정
        current_anchor = None
        if st.session_state.last_lat:
            current_anchor = (st.session_state.last_lat, st.session_state.last_lon)
        else:
            attended_all = day_df[day_df['참석여부'] == '참석'].sort_values('참석시간_dt', ascending=False)
            if not attended_all.empty:
                row = attended_all.iloc[0]
                if not pd.isna(row['위도']): current_anchor = (row['위도'], row['경도'])

        # 리스트 정렬 로직
        times = sorted(day_df['temp_time_dt'].dropna().unique())
        final_list = []
        for t in times:
            group = day_df[day_df['temp_time_dt'] == t].copy()
            group_att = group[group['참석여부'] == '참석'].sort_values('참석시간_dt')
            group_pending = group[group['참석여부'] == '미체크'].copy()
            if not group_pending.empty and current_anchor:
                group_pending['dist'] = group_pending.apply(lambda r: geodesic(current_anchor, (r['위도'], r['경도'])).meters if not pd.isna(r['위도']) else 999999, axis=1)
                group_pending = group_pending.sort_values('dist')
            group_no = group[group['참석여부'] == '불참석']
            final_list.append(pd.concat([group_att, group_pending, group_no]))

        display_df = pd.concat(final_list)

        # 3. 지도 출력 (불참석 제외 및 리스트 순서 동기화)
        st.subheader("📍 실시간 동선 지도")
        map_draw_df = display_df[display_df['참석여부'].isin(['참석', '미체크'])]
        map_draw_df = map_draw_df[map_draw_df['위도'].notna() & map_draw_df['경도'].notna()]
        
        if not map_draw_df.empty:
            # 첫 번째 마커 위치로 지도 중심 설정 (수정된 부분: 위0 -> 위도)
            m = folium.Map(location=[map_draw_df.iloc[0]['위도'], map_draw_df.iloc[0]['경도']], zoom_start=11)
            pts = []
            
            for _, r in map_draw_df.iterrows():
                icon_color = 'blue' if r['참석여부'] == '참석' else 'red'
                folium.Marker(
                    [r['위도'], r['경0' if False else '경도']], # 안전하게 경도 확인
                    popup=f"{r['시간']} {r['행사명']}", 
                    icon=folium.Icon(color=icon_color)
                ).add_to(m)
                pts.append([r['위도'], r['경도']])
            
            if len(pts) > 1:
                folium.PolyLine(pts, color="red", weight=3, opacity=0.8).add_to(m)
            folium_static(m)

        # 4. 일정 리스트 출력
        for _, row in display_df.iterrows():
            orig_idx = row['index']
            with st.container(border=True):
                st.markdown(f"### {row['시간']} | {row['행사명']}")
                st.caption(f"📍 {row['주소']}")
                status = str(row['참석여부']).strip()
                
                if status == "미체크":
                    c1, c2 = st.columns(2)
                    if c1.button("🟢 참석", key=f"at_{orig_idx}"):
                        update_sheet_status(orig_idx, "참석")
                        st.session_state.last_lat = row['위도']
                        st.session_state.last_lon = row['경도']
                        time.sleep(1) 
                        st.rerun()
                    if c2.button("🔴 불참석", key=f"no_{orig_idx}"):
                        update_sheet_status(orig_idx, "불참석")
                        time.sleep(1)
                        st.rerun()
                elif status == "불참석":
                    st.error(f"결과: {status}")
                    if st.button("🔄 재선택 (복구)", key=f"re_{orig_idx}"):
                        update_sheet_status(orig_idx, "미체크")
                        time.sleep(1)
                        st.rerun()
                else: 
                    st.success(f"결과: {status}")
                    if st.button("🔄 재선택", key=f"re_{orig_idx}"):
                        update_sheet_status(orig_idx, "미체크")
                        time.sleep(1)
                        st.rerun()
                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

except Exception as e:
    st.error(f"오류: {e}")
