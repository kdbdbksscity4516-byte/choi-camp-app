import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static

# 1. 설정 정보 (주소는 사무장님 주소 그대로 유지)
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbzlPtAOqvz0wSgbspGz9PbZuDcdd-BBtbbep_uEtCFTaBd4vYG5Pu6jo0dkESkVBIgI/exec"

KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

st.set_page_config(page_title="최웅식 캠프 실시간 동선", layout="centered")

def update_sheet_status(row_idx, status_text):
    api_url = f"{script_url}?row={row_idx}&status={urllib.parse.quote(status_text)}"
    try:
        res = requests.get(api_url, timeout=15)
        if "성공" in res.text:
            st.toast(f"✅ {status_text} 처리 완료")
            return True
    except: st.error("📡 시트 연결 실패")
    return False

st.markdown("""<style> div.stButton > button { width: 100% !important; height: 50px !important; } </style>""", unsafe_allow_html=True)
st.title("🚩 최웅식 캠프 실시간 동선")

try:
    df = pd.read_csv(f"{sheet_url}&t={now_kst.timestamp()}")
    df = df.fillna("")
    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    df['temp_time'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
    
    available_dates = sorted(df['날짜_dt'].unique())
    today_val = now_kst.date()
    default_idx = list(available_dates).index(today_val) if today_val in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    if st.button("🔄 데이터 새로고침"): st.rerun()
    st.divider()

    day_df = df[df['날짜_dt'] == selected_date].copy().reset_index()
    
    if not day_df.empty:
        # --- [동선 정렬 로직] ---
        times = sorted(day_df['temp_time'].unique())
        final_list = []
        last_ref_coords = None
        
        # 기준점 찾기
        attended_events = day_df[day_df['참석여부'] == '참석'].sort_values('temp_time')
        if not attended_events.empty and not pd.isna(attended_events.iloc[-1]['위도']):
            last_ref_coords = (attended_events.iloc[-1]['위도'], attended_events.iloc[-1]['경도'])

        for t in times:
            group = day_df[day_df['temp_time'] == t].copy()
            if not (group['참석여부'].isin(['참석', '불참석'])).any() and last_ref_coords:
                group['dist'] = group.apply(lambda r: geodesic(last_ref_coords, (r['위도'], r['경도'])).meters if not pd.isna(r['위도']) else 999999, axis=1)
                group = group.sort_values('dist')
            final_list.append(group)
            if not group.empty:
                # 다음 기준점: 이 시간대의 '참석' 중 마지막 것, 없으면 1등
                att_in_g = group[group['참석여부'] == '참석']
                target = att_in_g.iloc[-1] if not att_in_g.empty else group.iloc[0]
                if not pd.isna(target['위도']):
                    last_ref_coords = (target['위도'], target['경도'])

        display_df = pd.concat(final_list)

        # --- [1. 지도 표시 섹션] ---
        st.subheader("📍 실시간 동선 지도")
        
        # 유효한 좌표가 있는 일정만 추출하여 선 긋기
        map_df = display_df[display_df['위도'].notna() & display_df['경도'].notna()].copy()
        
        if not map_df.empty:
            # 지도 중심점 (첫 번째 일정 기준)
            m = folium.Map(location=[map_df.iloc[0]['위도'], map_df.iloc[0]['경도']], zoom_start=12)
            
            points = []
            for i, (_, row) in enumerate(map_df.iterrows()):
                coord = [row['위도'], row['경도']]
                points.append(coord)
                
                # 마커 색상: 참석은 파란색, 미체크는 빨간색
                color = 'blue' if row['참석여부'] == '참석' else 'red'
                folium.Marker(
                    location=coord,
                    popup=f"{row['시간']} {row['행사명']}",
                    icon=folium.Icon(color=color, icon='info-sign')
                ).add_to(m)
            
            # 빨간 실선 긋기 (동선 연결)
            if len(points) > 1:
                folium.PolyLine(points, color="red", weight=3, opacity=0.8).add_to(m)
            
            folium_static(m)
        else:
            st.info("좌표 정보가 없어 지도를 표시할 수 없습니다.")

        st.divider()

        # --- [2. 일정 상세 섹션] ---
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
                    if st.button("🔄 상태 수정", key=f"ed_{orig_idx}"):
                        if update_sheet_status(orig_idx, "미체크"): st.rerun()
                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")
    else:
        st.warning("데이터가 없습니다.")
except Exception as e:
    st.error(f"오류: {e}")
