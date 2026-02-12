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

def update_sheet_status(row_idx, status_text):
    api_url = f"{script_url}?row={row_idx}&status={urllib.parse.quote(status_text)}"
    try:
        res = requests.get(api_url, timeout=15)
        if "성공" in res.text:
            st.toast(f"✅ {status_text} 처리 완료")
            return True
    except:
        st.error("📡 시트 연결 실패")
    return False

st.markdown("""<style> div.stButton > button { width: 100% !important; height: 50px !important; } </style>""", unsafe_allow_html=True)

try:
    # 데이터 강제 로드 (캐시 무력화)
    fresh_url = f"{sheet_url}&t={int(time.time())}"
    df = pd.read_csv(fresh_url)
    df = df.fillna("")
    df.loc[df['참석여부'] == "", '참석여부'] = "미체크"
    
    # 기본 전처리
    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    df['날짜_str'] = df['날짜'].astype(str).str.strip()
    
    st.title("🚩 최웅식 후보자님 동선")

    available_dates = sorted([d for d in df['날짜_str'].unique() if d and d != "nan"])
    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = 0
    for i, d in enumerate(available_dates):
        if today_str in d:
            default_idx = i
            break
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    if st.button("🔄 새로운 일정 불러오기"):
        st.cache_data.clear()
        st.rerun()
    st.divider()

    day_df = df[df['날짜_str'] == selected_date].copy().reset_index()
    
    if not day_df.empty:
        # 시간 및 참석시간 데이터 정밀 변환
        day_df['temp_time_dt'] = pd.to_datetime(day_df['시간'], errors='coerce')
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        # --- [실시간 기준점 로직] ---
        # 1. 전체 일정 중 '참석'을 누른 것들 중 가장 마지막 시각(참석시간 기준)의 좌표를 찾음
        last_attended = day_df[day_df['참석여부'] == '참석'].sort_values('참석시간_dt', ascending=True)
        
        global_ref_coords = None
        if not last_attended.empty:
            last_row = last_attended.iloc[-1]
            if not pd.isna(last_row['위도']):
                global_ref_coords = (last_row['위도'], last_row['경도'])

        # 시간대별로 그룹화하여 정렬
        times = sorted(day_df['temp_time_dt'].dropna().unique())
        final_list = []
        
        current_ref = global_ref_coords # 현재 기준점

        for t in times:
            group = day_df[day_df['temp_time_dt'] == t].copy()
            
            # 이미 참석한 곳 (누른 순서대로)
            group_att = group[group['참석여부'] == '참석'].sort_values('참석시간_dt')
            
            # 아직 미체크인 곳 (현재 기준점 current_ref에서 가까운 순서대로)
            group_pending = group[group['참석여부'] == '미체크'].copy()
            if not group_pending.empty:
                if current_ref:
                    group_pending['dist'] = group_pending.apply(lambda r: geodesic(current_ref, (r['위도'], r['경도'])).meters if not pd.isna(r['위도']) else 999999, axis=1)
                else:
                    group_pending['dist'] = 0
                group_pending = group_pending.sort_values('dist')

            # 불참석 그룹
            group_no = group[group['참석여부'] == '불참석']
            
            sorted_group = pd.concat([group_att, group_pending, group_no])
            final_list.append(sorted_group)
            
            # 다음 시간대(혹은 다음 계산)를 위해 기준점 업데이트
            # 이 시간대에 참석한 곳이 있다면 그곳을 기준점으로, 없다면 미체크 중 가장 가까운 곳을 임시 기준점으로 활용
            if not group_att.empty:
                current_ref = (group_att.iloc[-1]['위도'], group_att.iloc[-1]['경도'])
            elif not group_pending.empty and current_ref is None:
                # 아예 처음 시작할 때 기준점이 없으면 미체크 첫번째 장소를 기준점으로 잡음
                current_ref = (group_pending.iloc[0]['위도'], group_pending.iloc[0]['경도'])

        display_df = pd.concat(final_list)

        # 지도 표시
        st.subheader("📍 실시간 동선 지도")
        m_df = display_df[display_df['참석여부'] != '불참석']
        m_df = m_df[m_df['위도'].notna() & m_df['경도'].notna()]
        if not m_df.empty:
            m = folium.Map(location=[m_df.iloc[0]['위도'], m_df.iloc[0]['경도']], zoom_start=11)
            pts = []
            for _, r in m_df.iterrows():
                color = 'blue' if r['참석여부'] == '참석' else 'red'
                folium.Marker([r['위도'], r['경도']], popup=r['행사명'], icon=folium.Icon(color=color)).add_to(m)
                pts.append([r['위도'], r['경도']])
            if len(pts) > 1:
                folium.PolyLine(pts, color="red", weight=3).add_to(m)
            folium_static(m)

        # 리스트 표시
        for _, row in display_df.iterrows():
            orig_idx = row['index']
            with st.container(border=True):
                st.markdown(f"### {row['시간']} | {row['행사명']}")
                st.caption(f"📍 {row['주소']}")
                status = str(row['참석여부']).strip()
                
                if status == "미체크":
                    c1, c2 = st.columns(2)
                    if c1.button("🟢 참석", key=f"at_{orig_idx}"):
                        if update_sheet_status(orig_idx, "참석"):
                            st.cache_data.clear() # 캐시 비우고
                            st.rerun()            # 즉시 새로고침
                    if c2.button("🔴 불참석", key=f"no_{orig_idx}"):
                        if update_sheet_status(orig_idx, "불참석"):
                            st.cache_data.clear()
                            st.rerun()
                else:
                    st.success(f"결과: {status}")
                    if st.button("🔄 재선택", key=f"re_{orig_idx}"):
                        if update_sheet_status(orig_idx, "미체크"):
                            st.cache_data.clear()
                            st.rerun()
                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")
    else:
        st.info("선택한 날짜에 일정이 없습니다.")

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
