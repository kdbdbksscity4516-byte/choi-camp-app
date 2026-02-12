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
    # 데이터 불러오기
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
        # --- [보강된 동선 정렬 로직] ---
        times = sorted(day_df['temp_time'].unique())
        final_list = []
        last_ref_coords = None
        
        # 1순위 기준점: 전체 일정 중 가장 마지막으로 '참석'한 곳
        attended_total = day_df[day_df['참석여부'] == '참석'].sort_values(['temp_time', 'index'])
        if not attended_total.empty and not pd.isna(attended_total.iloc[-1]['위도']):
            last_ref_coords = (attended_total.iloc[-1]['위도'], attended_total.iloc[-1]['경도'])

        for t in times:
            group = day_df[day_df['temp_time'] == t].copy()
            
            # 거리 계산 (이전 시간대 종착지 or 마지막 참석지 기준)
            if last_ref_coords:
                group['dist'] = group.apply(lambda r: geodesic(last_ref_coords, (r['위도'], r['경도'])).meters if not pd.isna(r['위도']) else 999999, axis=1)
            else:
                group['dist'] = 0

            # 정렬 우선순위: 1.참석 > 2.미체크 > 3.불참석 순서이며, 같은 상태 내에서는 거리순
            def get_priority(status):
                if status == '참석': return 0
                if status == '불참석': return 2
                return 1 # 미체크 및 기타

            group['priority'] = group['참석여부'].apply(get_priority)
            group = group.sort_values(by=['priority', 'dist'])
            
            final_list.append(group)
            
            # 다음 시간대를 위한 기준점 업데이트
            # 이 시간대 그룹의 마지막 '참석' 지점, 없으면 이 그룹의 1등(가장 가까운 곳)
            att_in_group = group[group['참석여부'] == '참석']
            target = att_in_group.iloc[-1] if not att_in_group.empty else group.iloc[0]
            if not pd.isna(target['위도']):
                last_ref_coords = (target['위도'], target['경도'])

        display_df = pd.concat(final_list)

        # --- [1. 지도 표시 섹션] ---
        st.subheader("📍 실시간 동선 지도")
        # 지도는 '참석'하거나 '미체크'인 것만 선으로 연결 (불참석은 제외)
        map_df = display_df[display_df['참석여부'] != '불참석'].copy()
        map_df = map_df[map_df['위도'].notna() & map_df['경도'].notna()]
        
        if not map_df.empty:
            m = folium.Map(location=[map_df.iloc[0]['위도'], map_df.iloc[0]['경도']], zoom_start=11)
            points = []
            for _, row in map_df.iterrows():
                coord = [row['위도'], row['경도']]
                points.append(coord)
                color = 'blue' if row['참석여부'] == '참석' else 'red'
                folium.Marker(
                    location=coord,
                    popup=f"{row['시간']} {row['행사명']}",
                    icon=folium.Icon(color=color, icon='info-sign')
                ).add_to(m)
            
            if len(points) > 1:
                folium.PolyLine(points, color="red", weight=3, opacity=0.8).add_to(m)
            folium_static(m)
        else:
            st.info("표시할 동선이 없습니다.")

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
