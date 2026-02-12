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
    except: st.error("📡 시트 연결 실패")
    return False

try:
    # 2. 데이터 강제 로드 및 전처리
    df = pd.read_csv(f"{sheet_url}&t={int(time.time())}")
    df = df.fillna("")
    df.loc[df['참석여부'] == "", '참석여부'] = "미체크"
    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    df['날짜_str'] = df['날짜'].astype(str).str.strip()
    
    st.title("🚩 최웅식 후보자님 동선 (최적화 모드)")

    available_dates = sorted([d for d in df['날짜_str'].unique() if d and d != "nan"])
    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = available_dates.index(today_str) if today_str in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    if st.button("🔄 데이터 강제 새로고침"):
        st.cache_data.clear()
        st.rerun()
    st.divider()

    day_df = df[df['날짜_str'] == selected_date].copy().reset_index()
    
    if not day_df.empty:
        # 시간 및 참석시간 변환
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        # --- [새로운 핵심 정렬 로직] ---
        # 1. 참석 완료 그룹 (누른 순서대로 상단 고정)
        attended_df = day_df[day_df['참석여부'] == '참석'].sort_values('참석시간_dt', ascending=True)
        
        # 2. 기준점(앵커) 찾기: 가장 최근에 '참석'을 누른 곳의 위치
        anchor_coords = None
        if not attended_df.empty:
            latest_attended = attended_df.iloc[-1]
            if not pd.isna(latest_attended['위도']):
                anchor_coords = (latest_attended['위도'], latest_attended['경도'])
        
        # 3. 미체크 그룹 처리
        pending_df = day_df[day_df['참석여부'] == '미체크'].copy()
        if not pending_df.empty:
            if anchor_coords:
                # 앵커가 있으면 모든 미체크 일정을 '앵커'와의 거리순으로 계산
                pending_df['dist'] = pending_df.apply(
                    lambda r: geodesic(anchor_coords, (r['위도'], r['경도'])).meters if not pd.isna(r['위도']) else 9999999, axis=1
                )
                pending_df = pending_df.sort_values('dist')
            else:
                # 앵커가 없으면(오늘 첫 시작) 시간순 정렬
                pending_df = pending_df.sort_values('시간')

        # 4. 불참석 그룹 (맨 아래)
        no_df = day_df[day_df['참석여부'] == '불참석']
        
        # 5. 최종 리스트 합치기: [참석완료] -> [가장 가까운 미체크들] -> [불참석]
        display_df = pd.concat([attended_df, pending_df, no_df])

        # --- 지도 및 리스트 출력 ---
        st.subheader("📍 실시간 최적화 동선")
        m_df = display_df[display_df['참석여부'] != '불참석']
        m_df = m_df[m_df['위도'].notna() & m_df['경도'].notna()]
        if not m_df.empty:
            m = folium.Map(location=[m_df.iloc[0]['위도'], m_df.iloc[0]['경도']], zoom_start=11)
            pts = [[r['위도'], r['경도']] for _, r in m_df.iterrows()]
            for _, r in m_df.iterrows():
                icon_color = 'blue' if r['참석여부'] == '참석' else 'red'
                folium.Marker([r['위도'], r['경도']], popup=r['행사명'], icon=folium.Icon(color=icon_color)).add_to(m)
            if len(pts) > 1: folium.PolyLine(pts, color="red", weight=3).add_to(m)
            folium_static(m)

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
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                    if c2.button("🔴 불참석", key=f"no_{orig_idx}"):
                        if update_sheet_status(orig_idx, "불참석"):
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                else:
                    st.success(f"결과: {status}")
                    if st.button("🔄 재선택", key=f"re_{orig_idx}"):
                        if update_sheet_status(orig_idx, "미체크"):
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")
    else:
        st.info("선택한 날짜에 일정이 없습니다.")
except Exception as e:
    st.error(f"오류: {e}")
