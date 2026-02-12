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
    # 시간 정렬을 위해 datetime 객체로 변환
    df['temp_time_dt'] = pd.to_datetime(df['시간'], errors='coerce')
    
    available_dates = sorted(df['날짜_dt'].unique())
    today_val = now_kst.date()
    default_idx = list(available_dates).index(today_val) if today_val in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    if st.button("🔄 데이터 새로고침"): st.rerun()
    st.divider()

    day_df = df[df['날짜_dt'] == selected_date].copy().reset_index()
    
    if not day_df.empty:
        # 참석시간 데이터 처리
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        # --- [새로운 정렬 로직: 시간대 우선 -> 그 안에서 누른 순서] ---
        times = sorted(day_df['temp_time_dt'].unique())
        final_list = []
        global_ref_coords = None
        
        for t in times:
            group = day_df[day_df['temp_time_dt'] == t].copy()
            
            # 1. '참석' 상태인 것들을 '누른 시간순'으로 먼저 배치
            # 2. 나머지는 '미체크' 상태인 것들을 '거리순'으로 배치
            
            group_attended = group[group['참석여부'] == '참석'].sort_values('참석시간_dt')
            
            # 기준점 업데이트 (이전 시간대 마지막 지점 활용)
            current_ref = global_ref_coords
            if not group_attended.empty:
                last_att = group_attended.iloc[-1]
                if not pd.isna(last_att['위도']):
                    current_ref = (last_att['위도'], last_att['경도'])

            # 미체크 항목 거리 계산
            if current_ref:
                group['dist'] = group.apply(lambda r: geodesic(current_ref, (r['위도'], r['경도'])).meters if not pd.isna(r['위도']) else 999999, axis=1)
            else:
                group['dist'] = 0

            def get_prio(status):
                if status == '참석': return 0
                if status == '불참석': return 2
                return 1

            group['prio'] = group['참석여부'].apply(get_prio)
            
            # 정렬 핵심: 상태(prio) -> 참석이면 누른시간순 / 아니면 거리순
            # 여기서는 복합 정렬을 위해 시퀀스를 합칩니다.
            group = group.sort_values(by=['prio', '참석시간_dt', 'dist'])
            final_list.append(group)
            
            # 다음 시간대를 위해 이 그룹의 마지막 지점(가장 유력한 현재 위치) 저장
            if not group.empty:
                # 불참석을 제외한 가장 마지막 지점 선택
                valid_group = group[group['참석여부'] != '불참석']
                if not valid_group.empty:
                    last_row = valid_group.iloc[-1]
                    if not pd.isna(last_row['위도']):
                        global_ref_coords = (last_row['위도'], last_row['경도'])

        display_df = pd.concat(final_list)

        # --- 지도 표시 섹션 ---
        st.subheader("📍 실시간 동선 지도")
        # 지도는 리스트에 정렬된 '참석' 및 '미체크' 순서 그대로 선을 긋습니다.
        map_df = display_df[display_df['참석여부'] != '불참석'].copy()
        map_df = map_df[map_df['위도'].notna() & map_df['경도'].notna()]
        
        if not map_df.empty:
            m = folium.Map(location=[map_df.iloc[0]['위도'], map_df.iloc[0]['경도']], zoom_start=11)
            points = []
            for _, row in map_df.iterrows():
                coord = [row['위도'], row['경도']]
                points.append(coord)
                color = 'blue' if row['참석여부'] == '참석' else 'red'
                folium.Marker(location=coord, popup=f"{row['시간']} {row['행사명']}", icon=folium.Icon(color=color)).add_to(m)
            
            if len(points) > 1:
                folium.PolyLine(points, color="red", weight=3).add_to(m)
            folium_static(m)

        st.divider()

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
