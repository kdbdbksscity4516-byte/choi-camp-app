import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
import time

# 1. 설정 정보 (사무장님 시트 주소)
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

# 2. 데이터 강제 로드 함수 (캐시 완전 차단)
@st.cache_data(ttl=1) # 1초만 저장하고 바로 삭제
def get_fresh_data(url):
    # 주소 뒤에 매번 바뀌는 숫자를 붙여 구글 서버를 속입니다.
    f_url = f"{url}&cachebust={int(time.time())}"
    return pd.read_csv(f_url)

try:
    df = get_fresh_data(sheet_url)
    df = df.fillna("")
    
    # 데이터가 아예 없는 경우 방지
    if df.empty:
        st.error("⚠️ 시트에 데이터가 하나도 없습니다. 시트를 확인해주세요.")
        st.stop()

    # 날짜 처리
    df['날짜_str'] = df['날짜'].astype(str).str.strip()
    available_dates = sorted([d for d in df['날짜_str'].unique() if d])
    
    if not available_dates:
        st.error("⚠️ 시트에서 '날짜'를 찾을 수 없습니다.")
        st.stop()

    st.title("🚩 최웅식 후보자님 동선")
    
    # 오늘 날짜 자동 선택
    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = 0
    for i, d in enumerate(available_dates):
        if today_str in d:
            default_idx = i
            break

    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    # 강제 새로고침 버튼 (누르면 모든 캐시 삭제)
    if st.button("🔄 새로운 일정 불러오기"):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # 해당 날짜 데이터만 필터링
    day_df = df[df['날짜_str'] == selected_date].copy().reset_index()
    
    if day_df.empty:
        st.info(f"선택한 날짜({selected_date})에 일정이 없습니다.")
    else:
        # 이후 정렬/지도/리스트 로직 (생략 없이 작동)
        day_df['위도'] = pd.to_numeric(day_df['위도'], errors='coerce')
        day_df['경도'] = pd.to_numeric(day_df['경도'], errors='coerce')
        day_df['temp_time_dt'] = pd.to_datetime(day_df['시간'], errors='coerce')
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        # [정렬 로직: 참석순 + 거리순]
        times = sorted(day_df['temp_time_dt'].dropna().unique())
        final_list = []
        last_ref = None
        
        # 마지막 참석지 찾기
        last_att = day_df[day_df['참석여부'] == '참석'].sort_values('참석시간_dt')
        if not last_att.empty:
            row = last_att.iloc[-1]
            if not pd.isna(row['위도']): last_ref = (row['위도'], row['경도'])

        for t in times:
            group = day_df[day_df['temp_time_dt'] == t].copy()
            group_att = group[group['참석여부'] == '참석'].sort_values('참석시간_dt')
            group_pending = group[group['참석여부'] == '미체크'].copy()
            if not group_pending.empty:
                if last_ref:
                    group_pending['dist'] = group_pending.apply(lambda r: geodesic(last_ref, (r['위도'], r['경도'])).meters if not pd.isna(r['위_도']) else 999999, axis=1)
                else: group_pending['dist'] = 0
                group_pending = group_pending.sort_values('dist')
            
            sorted_group = pd.concat([group_att, group_pending, group[group['참석여부'] == '불참석']])
            final_list.append(sorted_group)
            if not sorted_group.empty:
                v = sorted_group[sorted_group['참석여부'] != '불참석']
                if not v.empty and not pd.isna(v.iloc[-1]['위도']):
                    last_ref = (v.iloc[-1]['위도'], v.iloc[-1]['경도'])

        display_df = pd.concat(final_list)

        # 지도 및 리스트 출력
        st.subheader("📍 실시간 동선 지도")
        m_df = display_df[display_df['참석여부'] != '불참석']
        m_df = m_df[m_df['위도'].notna()]
        if not m_df.empty:
            m = folium.Map(location=[m_df.iloc[0]['위도'], m_df.iloc[0]['경도']], zoom_start=11)
            pts = []
            for _, r in m_df.iterrows():
                folium.Marker([r['위도'], r['경도']], popup=r['행사명'], icon=folium.Icon(color='blue' if r['참석여부']=='참석' else 'red')).add_to(m)
                pts.append([r['위도'], r['경도']])
            if len(pts) > 1: folium.PolyLine(pts, color="red").add_to(m)
            folium_static(m)

        for _, row in display_df.iterrows():
            orig_idx = row['index']
            with st.container(border=True):
                st.markdown(f"### {row['시간']} | {row['행사명']}")
                st.caption(f"📍 {row['주소']}")
                status = row['참석여부']
                if status == "미체크" or status == "":
                    c1, c2 = st.columns(2)
                    if c1.button("🟢 참석", key=f"at_{orig_idx}"):
                        if update_sheet_status(orig_idx, "참석"): st.rerun()
                    if c2.button("🔴 불참석", key=f"no_{orig_idx}"):
                        if update_sheet_status(orig_idx, "불참석"): st.rerun()
                else:
                    st.success(f"결과: {status}")
                    if st.button("🔄 재선택", key=f"re_{orig_idx}"):
                        if update_sheet_status(orig_idx, "미체크"): st.rerun()
                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

except Exception as e:
    st.error(f"오류: {e}")
