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

# 세션 상태에 마지막 확정 위치 저장
if 'last_lat' not in st.session_state: st.session_state.last_lat = None
if 'last_lon' not in st.session_state: st.session_state.last_lon = None

# 좌표 기반 지역구 판별 함수
def classify_by_coords(lat, lon):
    if pd.isna(lat) or pd.isna(lon): return "기타"
    if (lat > 37.517 and lon > 126.910) or (lat < 37.505): return "을"
    return "갑"

def update_sheet_status(row_idx, status_text):
    api_url = f"{script_url}?row={row_idx}&status={urllib.parse.quote(status_text)}"
    try:
        res = requests.get(api_url, timeout=10)
        return "성공" in res.text
    except: return False

try:
    df = pd.read_csv(f"{sheet_url}&t={int(time.time())}")
    df = df.fillna("")
    df.loc[df['참석여부'] == "", '참석여부'] = "미체크"
    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    df['날짜_str'] = df['날짜'].astype(str).str.strip()

    st.title("최웅식 후보 동선 최적화 & 활동 분석")

    if st.button("🔄 전체 새로고침 (F5)"):
        components.html("<script>window.parent.location.reload();</script>", height=0)
        st.stop()

    available_dates = sorted([d for d in df['날짜_str'].unique() if d and d != "nan"])
    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = available_dates.index(today_str) if today_str in available_dates else 0
    selected_date = st.selectbox("🗓️ 상세 동선 날짜 선택", available_dates, index=default_idx)

    day_df = df[df['날짜_str'] == selected_date].copy().reset_index()

    if not day_df.empty:
        day_df['temp_time_dt'] = pd.to_datetime(day_df['시간'], errors='coerce')
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        # --- [로직 핵심: 실시간 기준점 설정] ---
        # 1. 가장 최근에 '참석'을 누른 행사의 위치를 찾음
        attended_sorted = day_df[day_df['참석여부'] == '참석'].sort_values('참석시간_dt', ascending=False)
        
        if not attended_sorted.empty:
            latest_row = attended_sorted.iloc[0]
            if not pd.isna(latest_row['위도']):
                current_anchor = (latest_row['위도'], latest_row['경도'])
        else:
            current_anchor = None

        # 2. 정렬 실행
        times = sorted(day_df['temp_time_dt'].dropna().unique())
        final_list = []
        for t in times:
            group = day_df[day_df['temp_time_dt'] == t].copy()
            group_att = group[group['참석여부'] == '참석'].sort_values('참석시간_dt')
            group_pending = group[group['참석여부'] == '미체크'].copy()
            
            # 기준점이 있으면 미체크 항목들을 거리순 정렬
            if not group_pending.empty and current_anchor:
                group_pending['dist'] = group_pending.apply(lambda r: geodesic(current_anchor, (r['위도'], r['경도'])).meters if not pd.isna(r['위도']) else 999999, axis=1)
                group_pending = group_pending.sort_values('dist')
            
            group_no = group[group['참석여부'] == '불참석']
            final_list.append(pd.concat([group_att, group_pending, group_no]))

        display_df = pd.concat(final_list)

        # [지도 표시]
        st.subheader(f"📍 {selected_date} 상세 이동 경로")
        map_df_today = display_df[display_df['위도'].notna() & display_df['경도'].notna()]
        if not map_df_today.empty:
            m_today = folium.Map(location=[map_df_today.iloc[0]['위도'], map_df_today.iloc[0]['경도']], zoom_start=12)
            for _, r in map_df_today.iterrows():
                m_color = 'blue' if r['참석여부'] == '참석' else 'gray' if r['참석여부'] == '미체크' else 'red'
                folium.Marker([r['위도'], r['경도']], popup=f"{r['행사명']}", icon=folium.Icon(color=m_color)).add_to(m_today)
            folium_static(m_today)

        # [리스트 및 박스 디자인]
        st.subheader("📝 오늘 주요 일정 리스트")
        for _, row in display_df.iterrows():
            orig_idx = row['index']
            with st.container(border=True):
                st.markdown(f"### {row['시간']} | {row['행사명']}")
                status = str(row['참석여부']).strip()
                if status == "미체크":
                    c1, c2 = st.columns(2)
                    if c1.button("🟢 참석", key=f"at_{orig_idx}"):
                        update_sheet_status(orig_idx, "참석")
                        # 누르는 순간 세션에 위치 저장하여 즉시 반영
                        st.session_state.last_lat, st.session_state.last_lon = row['위도'], row['경도']
                        time.sleep(1); st.rerun()
                    if c2.button("🔴 불참석", key=f"no_{orig_idx}"):
                        update_sheet_status(orig_idx, "불참석"); time.sleep(1); st.rerun()
                elif status == "불참석":
                    st.error(f"결과: {status}")
                    if st.button("🔄 재선택", key=f"re_no_{orig_idx}"): update_sheet_status(orig_idx, "미체크"); time.sleep(1); st.rerun()
                else:
                    st.success(f"결과: {status}")
                    if st.button("🔄 재선택", key=f"re_at_{orig_idx}"): update_sheet_status(orig_idx, "미체크"); time.sleep(1); st.rerun()
                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

    # [좌표 기반 통계 - 맨 하단]
    st.divider()
    st.subheader("📊 좌표 기반 지역구별 참석 현황")
    attended_df = df[df['참석여부'].str.strip() == '참석'].copy()
    if not attended_df.empty:
        attended_df['지역구_auto'] = attended_df.apply(lambda x: classify_by_coords(x['위도'], x['경도']), axis=1)
        st.markdown("#### [영등포구 요약]")
        st.dataframe(pd.DataFrame({"갑 참석": [len(attended_df[attended_df['지역구_auto'] == "갑"])], "을 참석": [len(attended_df[attended_df['지역구_auto'] == "을"])]}), use_container_width=True, hide_index=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### [갑] 상세")
            st.dataframe(attended_df[attended_df['지역구_auto'] == "갑"][['날짜', '행사명']], use_container_width=True, hide_index=True)
        with col2:
            st.markdown("#### [을] 상세")
            st.dataframe(attended_df[attended_df['지역구_auto'] == "을"][['날짜', '행사명']], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"오류: {e}")
    
