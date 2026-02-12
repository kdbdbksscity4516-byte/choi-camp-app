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
    # 데이터 강제 로드
    df = pd.read_csv(f"{sheet_url}&t={int(time.time())}")
    df = df.fillna("")
    df.loc[df['참석여부'] == "", '참석여부'] = "미체크"
    
    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    df['날짜_str'] = df['날짜'].astype(str).str.strip()
    
    st.title("🚩 최웅식 후보자님 스케줄")

    available_dates = sorted([d for d in df['날짜_str'].unique() if d and d != "nan"])
    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = available_dates.index(today_str) if today_str in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    if st.button("🔄 일정 새로고침"):
        st.cache_data.clear()
        st.rerun()
    st.divider()

    day_df = df[df['날짜_str'] == selected_date].copy().reset_index()
    
    if not day_df.empty:
        day_df['temp_time_dt'] = pd.to_datetime(day_df['시간'], errors='coerce')
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        # 1. 오늘 전체에서 가장 최근 '참석' 누른 위치 찾기 (기준점)
        attended_all = day_df[day_df['참석여부'] == '참석'].sort_values('참석시간_dt', ascending=False)
        last_coords = None
        if not attended_all.empty:
            row = attended_all.iloc[0]
            if not pd.isna(row['위도']): last_coords = (row['위도'], row['경도'])

        # 2. 시간대별 그룹핑 (시간 순서 보장)
        times = sorted(day_df['temp_time_dt'].dropna().unique())
        final_list = []

        for t in times:
            group = day_df[day_df['temp_time_dt'] == t].copy()
            
            # (A) 이 시간대 참석 완료: 누른 시간 순서대로 (맨 위)
            group_att = group[group['참석여부'] == '참석'].sort_values('참석시간_dt')
            
            # (B) 이 시간대 미체크: 마지막 참석 위치(전주 등)에서 가까운 순
            group_pending = group[group['참석여부'] == '미체크'].copy()
            if not group_pending.empty:
                if last_coords:
                    group_pending['dist'] = group_pending.apply(
                        lambda r: geodesic(last_coords, (r['위도'], r['경도'])).meters if not pd.isna(r['위도']) else 9999999, axis=1
                    )
                    group_pending = group_pending.sort_values('dist')
            
            group_no = group[group['참석여부'] == '불참석']
            
            # 시간대 내부에서만 정렬하여 합침
            final_list.append(pd.concat([group_att, group_pending, group_no]))

        display_df = pd.concat(final_list)

        # 지도 및 리스트 출력
        st.subheader("📍 현재 위치 기반 동선")
        m_df = display_df[display_df['참석여부'] != '불참석']
        m_df = m_df[m_df['위도'].notna() & m_df['경도'].notna()]
        if not m_df.empty:
            m = folium.Map(location=[m_df.iloc[0]['위도'], m_df.iloc[0]['경도']], zoom_start=11)
            pts = [[r['위도'], r['경도']] for _, r in m_df.iterrows()]
            for _, r in m_df.iterrows():
                folium.Marker([r['위도'], r['경도']], popup=r['행사명'], icon=folium.Icon(color='blue' if r['참석여부']=='참석' else 'red')).add_to(m)
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
                            time.sleep(1)
                            st.rerun()
                    if c2.button("🔴 불참석", key=f"no_{orig_idx}"):
                        if update_sheet_status(orig_idx, "불참석"):
                            time.sleep(1)
                            st.rerun()
                else:
                    st.success(f"결과: {status}")
                    if st.button("🔄 재선택", key=f"re_{orig_idx}"):
                        if update_sheet_status(orig_idx, "미체크"):
                            time.sleep(1)
                            st.rerun()
                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")
    else:
        st.info("선택한 날짜에 일정이 없습니다.")
except Exception as e:
    st.error(f"오류: {e}")
