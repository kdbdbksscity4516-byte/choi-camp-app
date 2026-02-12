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
    # 데이터 로드 (캐시 방지 타임스탬프 포함)
    df = pd.read_csv(f"{sheet_url}&t={now_kst.timestamp()}")
    df = df.fillna("")
    
    # 상단 사진 표시
    if '사진' in df.columns:
        photo_list = [p for p in df['사진'].tolist() if str(p).startswith('http')]
        if photo_list: st.image(photo_list[0], use_container_width=True)

    st.title("🚩 최웅식 후보자님 동선")

    # 데이터 전처리
    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    # 날짜 형식을 문자열로 통일하여 비교 오류 방지
    df['날짜_str'] = pd.to_datetime(df['날짜']).dt.strftime('%Y-%m-%d')
    df['temp_time_dt'] = pd.to_datetime(df['시간'], errors='coerce')
    
    available_dates = sorted(df['날짜_str'].unique())
    today_str = now_kst.strftime('%Y-%m-%d')
    
    # 기본 날짜 선택 로직
    default_idx = 0
    if today_str in available_dates:
        default_idx = list(available_dates).index(today_str)
    
    selected_date_str = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    if st.button("🔄 데이터 새로고침"): st.rerun()
    st.divider()

    # 선택된 날짜의 데이터 필터링
    day_df = df[df['날짜_str'] == selected_date_str].copy().reset_index()
    
    if not day_df.empty:
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        # --- [정렬 로직] ---
        times = sorted(day_df['temp_time_dt'].unique())
        final_list = []
        last_ref_coords = None
        
        # 기준점 찾기 (가장 최근 참석 지점)
        last_att_df = day_df[day_df['참석여부'] == '참석'].sort_values('참석시간_dt')
        if not last_att_df.empty:
            row = last_att_df.iloc[-1]
            if not pd.isna(row['위도']):
                last_ref_coords = (row['위도'], row['경도'])

        for t in times:
            group = day_df[day_df['temp_time_dt'] == t].copy()
            
            # 1. 참석 그룹 (누른 순서)
            group_att = group[group['참석여부'] == '참석'].sort_values('참석시간_dt')
            
            # 2. 미체크 그룹 (거리순)
            group_pending = group[group['참석여부'] == '미체크'].copy()
            if not group_pending.empty:
                if last_ref_coords:
                    group_pending['dist'] = group_pending.apply(lambda r: geodesic(last_ref_coords, (r['위도'], r['경도'])).meters if not pd.isna(r['위도']) else 9999999, axis=1)
                else:
                    group_pending['dist'] = 0
                group_pending = group_pending.sort_values('dist')

            # 3. 불참석 그룹
            group_no = group[group['참석여부'] == '불참석']

            # 시간대별 정렬 합치기
            sorted_group = pd.concat([group_att, group_pending, group_no])
            final_list.append(sorted_group)
            
            # 다음 시간대 거리 계산을 위한 기준점 갱신
            valid_last = sorted_group[sorted_group['참석여부'] != '불참석']
            if not valid_last.empty and not pd.isna(valid_last.iloc[-1]['위도']):
                last_ref_coords = (valid_last.iloc[-1]['위도'], valid_last.iloc[-1]['경도'])

        display_df = pd.concat(final_list)

        # --- 지도 섹션 ---
        st.subheader("📍 실시간 동선 지도")
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

        # --- 리스트 섹션 ---
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
        st.warning(f"'{selected_date_str}' 날짜에 등록된 행사가 없습니다. 시트의 날짜를 확인해 주세요.")
except Exception as e:
    st.error(f"오류 발생: {e}")
