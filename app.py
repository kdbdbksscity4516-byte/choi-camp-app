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
    df = pd.read_csv(f"{sheet_url}&t={int(time.time())}")
    df = df.fillna("")
    df.loc[df['참석여부'] == "", '참석여부'] = "미체크"
    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    df['날짜_str'] = df['날짜'].astype(str).str.strip()

    st.title("🚩 최웅식 후보자님 실시간 동선")

    if st.button("🔄 전체 새로고침 (F5)"):
        components.html("<script>window.parent.location.reload();</script>", height=0)
        st.stop()

    available_dates = sorted([d for d in df['날짜_str'].unique() if d and d != "nan"])
    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = available_dates.index(today_str) if today_str in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)

    day_df = df[df['날짜_str'] == selected_date].copy().reset_index()

    if not day_df.empty:
        day_df['temp_time_dt'] = pd.to_datetime(day_df['시간'], errors='coerce')
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        current_anchor = None
        if st.session_state.last_lat:
            current_anchor = (st.session_state.last_lat, st.session_state.last_lon)
        else:
            attended_all = day_df[day_df['참석여부'] == '참석'].sort_values('참석시간_dt', ascending=False)
            if not attended_all.empty:
                row = attended_all.iloc[0]
                if not pd.isna(row['위도']): current_anchor = (row['위도'], row['경도'])

        # 리스트 정렬 로직 (이전과 동일하게 유지)
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

        # 3. 지도 출력 (마커 색상 및 선 연결 로직 수정)
        st.subheader("📍 실시간 동선 지도")
        # 모든 항목(참석, 미체크, 불참석) 중 좌표가 있는 것들
        map_df = display_df[display_df['위도'].notna() & display_df['경도'].notna()]
        
        if not map_df.empty:
            m = folium.Map(location=[map_df.iloc[0]['위도'], map_df.iloc[0]['경도']], zoom_start=11)
            line_pts = [] # 선을 그을 좌표들 (참석, 미체크만 포함)
            
            for _, r in map_df.iterrows():
                # 상태별 마커 설정
                if r['참석여부'] == '참석':
                    m_color = 'blue'
                    m_icon = 'check'
                    line_pts.append([r['위도'], r['경도']]) # 선 연결 포함
                elif r['참석여부'] == '미체크':
                    m_color = 'gray'
                    m_icon = 'time'
                    line_pts.append([r['위도'], r['경도']]) # 선 연결 포함
                else: # 불참석
                    m_color = 'red'
                    m_icon = 'remove'
                    # 불참석은 line_pts에 추가하지 않음 (선에서 제외)
                
                folium.Marker(
                    [r['위도'], r['경도']], 
                    popup=f"[{r['참석여부']}] {r['시간']} {r['행사명']}", 
                    icon=folium.Icon(color=m_color, icon=m_icon)
                ).add_to(m)
            
            # 실시간 동선 선 긋기 (참석 -> 미체크 순서대로)
            if len(line_pts) > 1:
                folium.PolyLine(line_pts, color="red", weight=3, opacity=0.8).add_to(m)
            folium_static(m)

        # 4. 일정 리스트 출력 (기존 기능 유지)
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
                        st.session_state.last_lat, st.session_state.last_lon = row['위도'], row['경도']
                        time.sleep(1); st.rerun()
                    if c2.button("🔴 불참석", key=f"no_{orig_idx}"):
                        update_sheet_status(orig_idx, "불참석")
                        time.sleep(1); st.rerun()
                elif status == "불참석":
                    st.error(f"결과: {status}")
                    if st.button("🔄 재선택 (복구)", key=f"re_{orig_idx}"):
                        update_sheet_status(orig_idx, "미체크")
                        time.sleep(1); st.rerun()
                else: 
                    st.success(f"결과: {status}")
                    if st.button("🔄 재선택", key=f"re_{orig_idx}"):
                        update_sheet_status(orig_idx, "미체크")
                        time.sleep(1); st.rerun()
                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

except Exception as e:
    st.error(f"오류: {e}")
