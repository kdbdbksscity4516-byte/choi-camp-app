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

# 1. 기본 설정 및 세션 초기화
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbzlPtAOqvz0wSgbspGz9PbZuDcdd-BBtbbep_uEtCFTaBd4vYG5Pu6jo0dkESkVBIgI/exec"

KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

st.set_page_config(page_title="최웅식 후보 동선 관리", layout="wide")

if 'last_lat' not in st.session_state: st.session_state.last_lat = None
if 'last_lon' not in st.session_state: st.session_state.last_lon = None

# 지역구 그룹핑 정의
GAP_LIST = ["영등포동", "영등포본동", "당산1동", "당산2동", "도림동", "문래동", "양평1동", "양평2동", "신길1동", "신길2동", "신길3동"]
EUL_LIST = ["여의동", "신길4동", "신길5동", "신길6동", "신길7동", "대림1동", "대림2동", "대림3동"]

def get_dong_group(address):
    address = str(address)
    for dong in GAP_LIST:
        if dong in address:
            if "영등포동" in dong or "영등포본동" in dong: return "영등포구 갑", "영등포(본)동"
            if "당산" in dong: return "영등포구 갑", "당산1·2동"
            if "도림동" in dong: return "영등포구 갑", "도림동"
            if "문래동" in dong: return "영등포구 갑", "문래동"
            if "양평" in dong: return "영등포구 갑", "양평1·2동"
            if "신길1" in dong or "신길2" in dong or "신길3" in dong: return "영등포구 갑", "신길1·2·3동"
    for dong in EUL_LIST:
        if dong in address:
            if "여의동" in dong: return "영등포구 을", "여의동"
            if "신길4" in dong or "신길5" in dong or "신길6" in dong or "신길7" in dong: return "영등포구 을", "신길4·5·6·7동"
            if "대림" in dong: return "영등포구 을", "대림1·2·3동"
    return "기타", "기타"

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

    # [1] 날짜 선택 및 상세 지도/리스트
    available_dates = sorted([d for d in df['날짜_str'].unique() if d and d != "nan"])
    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = available_dates.index(today_str) if today_str in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)

    day_df = df[df['날짜_str'] == selected_date].copy().reset_index()
    if not day_df.empty:
        # (상세 지도 및 리스트 로직 유지...)
        # ... [중략] ...
        st.subheader("📝 오늘 주요 일정 리스트")
        for _, row in day_df.iterrows():
            orig_idx = row['index']
            with st.container(border=True):
                st.markdown(f"### {row['시간']} | {row['행사명']}")
                status = str(row['참석여부']).strip()
                if status == "미체크":
                    c1, c2 = st.columns(2)
                    if c1.button("🟢 참석", key=f"at_{orig_idx}"):
                        update_sheet_status(orig_idx, "참석"); time.sleep(1); st.rerun()
                    if c2.button("🔴 불참석", key=f"no_{orig_idx}"):
                        update_sheet_status(orig_idx, "불참석"); time.sleep(1); st.rerun()
                else:
                    st.write(f"결과: {status}")
                    if st.button("🔄 상태 변경", key=f"re_{orig_idx}"):
                        update_sheet_status(orig_idx, "미체크"); time.sleep(1); st.rerun()

    # [2] 지역구별 참석 횟수 현황 (이미지 스타일)
    st.divider()
    st.subheader("📊 지역구별 참석 횟수 현황")
    attended_df = df[df['참석여부'] == '참석'].copy()
    attended_df[['지역구', '분류동']] = attended_df.apply(lambda x: pd.Series(get_dong_group(x['주소'])), axis=1)

    sum_data = pd.DataFrame({"갑": [len(attended_df[attended_df['지역구'] == "영등포구 갑"])], 
                             "을": [len(attended_df[attended_df['지역구'] == "영등포구 을"])]})
    st.table(sum_data)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### [갑]")
        gap_target = ["영등포(본)동", "당산1·2동", "도림동", "문래동", "양평1·2동", "신길1·2·3동"]
        gap_res = [{"동네": d, "참석 횟수": len(attended_df[(attended_df['지역구']=="영등포구 갑") & (attended_df['분류동']==d)])} for d in gap_target]
        st.table(pd.DataFrame(gap_res))
    with col2:
        st.markdown("### [을]")
        eul_target = ["여의동", "신길4·5·6·7동", "대림1·2·3동"]
        eul_res = [{"동네": d, "참석 횟수": len(attended_df[(attended_df['지역구']=="영등포구 을") & (attended_df['분류동']==d)])} for d in eul_target]
        st.table(pd.DataFrame(eul_res))

    # [3] 누적 활동 지도 (미체크 제외, 참석/불참만 표시)
    st.divider()
    st.subheader("🗺️ 선거 활동 누적 분포 (참석/불참석)")
    st.caption("파란핀: 참석 | 빨간핀: 불참석 (미체크 항목은 표시되지 않습니다.)")
    map_filter_df = df[df['참석여부'].isin(['참석', '불참석']) & df['위도'].notna()].copy()
    
    if not map_filter_df.empty:
        m_all = folium.Map(location=[map_filter_df['위도'].mean(), map_filter_df['경도'].mean()], zoom_start=12)
        for _, r in map_filter_df.iterrows():
            m_color = 'blue' if r['참석여부'] == '참석' else 'red'
            m_icon = 'check' if r['참석여부'] == '참석' else 'remove'
            folium.Marker([r['위도'], r['경도']], popup=f"{r['날짜']} {r['행사명']}", 
                          icon=folium.Icon(color=m_color, icon=m_icon)).add_to(m_all)
        folium_static(m_all)

except Exception as e:
    st.error(f"오류: {e}")
