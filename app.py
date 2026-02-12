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

# 1. 설정 및 세션 초기화
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbzlPtAOqvz0wSgbspGz9PbZuDcdd-BBtbbep_uEtCFTaBd4vYG5Pu6jo0dkESkVBIgI/exec"
KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

st.set_page_config(page_title="최웅식 후보 동선 관리", layout="wide")

if 'last_lat' not in st.session_state: st.session_state.last_lat = None
if 'last_lon' not in st.session_state: st.session_state.last_lon = None

# 좌표 기반 지역구 판별 (통계용)
def classify_by_coords(lat, lon):
    if pd.isna(lat) or pd.isna(lon): return "기타"
    if (lat > 37.517 and lon > 126.910) or (lat < 37.505): return "을"
    return "갑"

def update_sheet_status(row_idx, status_text):
    # 참석 시 '참석시간'을 현재 시간으로 함께 기록하도록 스크립트가 구성되어야 함
    api_url = f"{script_url}?row={row_idx}&status={urllib.parse.quote(status_text)}"
    try:
        res = requests.get(api_url, timeout=10)
        return "성공" in res.text
    except: return False

try:
    # 2. 데이터 로드
    df = pd.read_csv(f"{sheet_url}&t={int(time.time())}")
    df = df.fillna("")
    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    df['날짜_str'] = df['날짜'].astype(str).str.strip()
    df.loc[df['참석여부'] == "", '참석여부'] = "미체크"

    st.title("최웅식 후보 동선 최적화 & 활동 분석")

    if st.button("🔄 전체 새로고침 (F5)"):
        components.html("<script>window.parent.location.reload();</script>", height=0)
        st.stop()

    # 3. 당일 동선 섹션
    available_dates = sorted([d for d in df['날짜_str'].unique() if d and d != "nan"])
    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = available_dates.index(today_str) if today_str in available_dates else 0
    selected_date = st.selectbox("🗓️ 상세 동선 날짜 선택", available_dates, index=default_idx)

    day_df = df[df['날짜_str'] == selected_date].copy().reset_index()

    if not day_df.empty:
        # 시간 데이터 변환
        day_df['temp_time_dt'] = pd.to_datetime(day_df['시간'], errors='coerce')
        # 시트의 '참석시간' 열을 기준으로 실제 누른 순서를 판단함
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        # --- [핵심: 정렬 로직 전면 수정] ---
        # 1. '참석'인 항목은 '참석시간' 순서대로 맨 위에 나열 (누른 순서 보장)
        # 2. '미체크'인 항목은 현재 위치(last_lat) 기준으로 가까운 순 정렬
        # 3. '불참석'은 맨 아래 배치
        
        attended = day_df[day_df['참석여부'] == '참석'].sort_values('참석시간_dt')
        pending = day_df[day_df['참석여부'] == '미체크'].copy()
        absent = day_df[day_df['참석여부'] == '불참석']
        
        if not pending.empty:
            anchor = (st.session_state.last_lat, st.session_state.last_lon) if st.session_state.last_lat else None
            if anchor:
                pending['dist'] = pending.apply(lambda r: geodesic(anchor, (r['위도'], r['경도'])).meters if not pd.isna(r['위도']) else 999999, axis=1)
                pending = pending.sort_values(['temp_time_dt', 'dist']) # 시간대 우선, 그 안에서 거리순
            else:
                pending = pending.sort_values('temp_time_dt')

        display_df = pd.concat([attended, pending, absent])

        # [당일 지도]
        st.subheader(f"📍 {selected_date} 실시간 동선 지도")
        map_df_today = display_df[display_df['위도'].notna() & display_df['경도'].notna()]
        if not map_df_today.empty:
            m_today = folium.Map(location=[map_df_today.iloc[0]['위도'], map_df_today.iloc[0]['경도']], zoom_start=13)
            line_pts = [[r['위도'], r['경도']] for _, r in display_df[display_df['참석여부'] == '참석'].iterrows()]
            for _, r in map_df_today.iterrows():
                m_color = 'blue' if r['참석여부'] == '참석' else 'gray' if r['참석여부'] == '미체크' else 'red'
                folium.Marker([r['위도'], r['경도']], popup=f"{r['행사명']}", icon=folium.Icon(color=m_color)).add_to(m_today)
            if len(line_pts) > 1:
                folium.PolyLine(line_pts, color="blue", weight=3, opacity=0.8, dash_array='5').add_to(m_today)
            folium_static(m_today)

        # [리스트 및 버튼]
        st.subheader("📝 오늘 주요 일정 리스트")
        for _, row in display_df.iterrows():
            orig_idx = row['index']
            with st.container(border=True):
                st.markdown(f"### {row['시간']} | {row['행사명']}")
                status = str(row['참석여부']).strip()
                if status == "미체크":
                    c1, c2 = st.columns(2)
                    if c1.button("🟢 참석 처리", key=f"at_{orig_idx}"):
                        update_sheet_status(orig_idx, "참석")
                        st.session_state.last_lat, st.session_state.last_lon = row['위도'], row['경도']
                        time.sleep(1); st.rerun()
                    if c2.button("🔴 불참 처리", key=f"no_{orig_idx}"):
                        update_sheet_status(orig_idx, "불참석"); time.sleep(1); st.rerun()
                elif status == "참석":
                    st.success(f"✅ 완료 (기록시간: {row['참석시간']})")
                    if st.button("🔄 취소", key=f"re_{orig_idx}"): update_sheet_status(orig_idx, "미체크"); time.sleep(1); st.rerun()
                elif status == "불참석":
                    st.error("❌ 불참석")
                    if st.button("🔄 취소", key=f"re_no_{orig_idx}"): update_sheet_status(orig_idx, "미체크"); time.sleep(1); st.rerun()
                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

    # 4. 분석 섹션
    st.divider()
    st.subheader("📊 좌표 기반 활동 통계")
    attended_df = df[df['참석여부'].str.strip() == '참석'].copy()
    if not attended_df.empty:
        attended_df['지역구_auto'] = attended_df.apply(lambda x: classify_by_coords(x['위도'], x['경도']), axis=1)
        st.markdown("#### [영등포구 요약]")
        summary_data = pd.DataFrame({"갑 참석": [len(attended_df[attended_df['지역구_auto'] == "갑"])], "을 참석": [len(attended_df[attended_df['지역구_auto'] == "을"])]})
        st.dataframe(summary_data, use_container_width=True, hide_index=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### [영등포구 갑]")
            st.dataframe(attended_df[attended_df['지역구_auto'] == "갑"][['날짜', '행사명']], use_container_width=True, hide_index=True)
        with c2:
            st.markdown("#### [영등포구 을]")
            st.dataframe(attended_df[attended_df['지역구_auto'] == "을"][['날짜', '행사명']], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"오류: {e}")
