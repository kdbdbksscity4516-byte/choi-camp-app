import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static

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

st.markdown("""<style> div.stButton > button { width: 100% !important; height: 50px !important; } </style>""", unsafe_allow_html=True)

try:
    df = pd.read_csv(f"{sheet_url}&t={now_kst.timestamp()}")
    df = df.fillna("")
    
    if '사진' in df.columns:
        photo_list = [p for p in df['사진'].tolist() if str(p).startswith('http')]
        if photo_list: st.image(photo_list[0], use_container_width=True)

    st.title("🚩 최웅식 후보자님 동선")

    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    df['temp_time_dt'] = pd.to_datetime(df['시간'], errors='coerce')
    
    available_dates = sorted(df['날짜_dt'].unique())
    today_val = now_kst.date()
    default_idx = list(available_dates).index(today_val) if today_val in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    if st.button("🔄 데이터 새로고침"): st.rerun()
    st.divider()

    day_df = df[df['날짜_dt'] == selected_date].copy().reset_index()
    
    if not day_df.empty:
        # 참석시간 데이터 정밀 변환
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        # --- [지도용 선긋기 순서 데이터 생성] ---
        # 1. '참석' 지점들만 따로 뽑아 누른 시간 순서대로 정렬 (이게 실제 이동 경로)
        attended_points = day_df[day_df['참석여부'] == '참석'].sort_values(by=['참석시간_dt', 'index']).copy()
        
        # 2. '미체크' 지점들은 원래 하던 대로 시간순 -> 거리순 정렬
        pending_points = day_df[day_df['참석여부'] == '미체크'].sort_values(by=['temp_time_dt', 'index']).copy()
        
        # 3. 지도용 데이터 합치기 (참석지가 무조건 먼저, 그 다음 미체크)
        # ※ 이렇게 하면 부산을 먼저 누르면 부산이 선의 앞부분에 옵니다.
        map_df_final = pd.concat([attended_points, pending_points])
        map_df_final = map_df_final[map_df_final['위도'].notna() & map_df_final['경도'].notna()]

        # --- 지도 섹션 ---
        st.subheader("📍 실시간 동선 지도")
        if not map_df_final.empty:
            m = folium.Map(location=[map_df_final.iloc[0]['위도'], map_df_final.iloc[0]['경도']], zoom_start=11)
            points = []
            for _, row in map_df_final.iterrows():
                coord = [row['위도'], row['경도']]
                points.append(coord)
                color = 'blue' if row['참석여부'] == '참석' else 'red'
                folium.Marker(location=coord, popup=f"{row['시간']} {row['행사명']}", icon=folium.Icon(color=color)).add_to(m)
            
            if len(points) > 1:
                folium.PolyLine(points, color="red", weight=3).add_to(m)
            folium_static(m)

        st.divider()

        # --- [리스트 표시용 정렬 로직: 시간대별 그룹 유지] ---
        times = sorted(day_df['temp_time_dt'].unique())
        display_list = []
        for t in times:
            group = day_df[day_df['temp_time_dt'] == t].copy()
            # 리스트는 보기 편하게 '참석'이 위로 오고 그 안에서는 누른 순서
            group['prio'] = group['참석여부'].apply(lambda x: 0 if x == '참석' else 2 if x == '불참석' else 1)
            group = group.sort_values(by=['prio', '참석시간_dt'])
            display_list.append(group)
        
        display_df = pd.concat(display_list)

        # --- 일정 상세 리스트 ---
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
                    if st.button("🔄 재선택", key=f"ed_{orig_idx}"):
                        if update_sheet_status(orig_idx, "미체크"): st.rerun()
                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")
    else:
        st.warning("데이터가 없습니다.")
except Exception as e:
    st.error(f"오류 발생: {e}")
