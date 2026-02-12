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

# 1. 설정 및 세션 상태 초기화
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbzlPtAOqvz0wSgbspGz9PbZuDcdd-BBtbbep_uEtCFTaBd4vYG5Pu6jo0dkESkVBIgI/exec"

KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

st.set_page_config(page_title="최웅식 후보 동선 관리", layout="wide")

if 'last_lat' not in st.session_state: st.session_state.last_lat = None
if 'last_lon' not in st.session_state: st.session_state.last_lon = None

# 지역구 분류 함수
GAP_LIST = ["영등포동", "영등포본동", "당산1동", "당산2동", "도림동", "문래동", "양평1동", "양평2동", "신길1동", "신길2동", "신길3동"]
EUL_LIST = ["여의동", "신길4동", "신길5동", "신길6동", "신길7동", "대림1동", "대림2동", "대림3동"]

def get_dong_group(address):
    address = str(address)
    for dong in GAP_LIST:
        if dong in address:
            if "영등포동" in dong or "영등포본동" in dong: return "갑", "영등포(본)동"
            if "당산" in dong: return "갑", "당산1·2동"
            if "도림동" in dong: return "갑", "도림동"
            if "문래동" in dong: return "갑", "문래동"
            if "양평" in dong: return "갑", "양평1·2동"
            if "신길1" in dong or "신길2" in dong or "신길3" in dong: return "갑", "신길1·2·3동"
    for dong in EUL_LIST:
        if dong in address:
            if "여의동" in dong: return "을", "여의동"
            if "신길4" in dong or "신길5" in dong or "신길6" in dong or "신길7" in dong: return "을", "신길4·5·6·7동"
            if "대림" in dong: return "을", "대림1·2·3동"
    return "기타", "기타"

def update_sheet_status(row_idx, status_text):
    api_url = f"{script_url}?row={row_idx}&status={urllib.parse.quote(status_text)}"
    try:
        res = requests.get(api_url, timeout=10)
        return "성공" in res.text
    except: return False

try:
    # 데이터 로드
    df = pd.read_csv(f"{sheet_url}&t={int(time.time())}")
    df = df.fillna("")
    df.loc[df['참석여부'] == "", '참석여부'] = "미체크"
    # [수정] 오타 절대 방지: 위도/경도 숫자 변환
    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    df['날짜_str'] = df['날짜'].astype(str).str.strip()

    st.title("최웅식 후보 동선 최적화 & 활동 분석")

    if st.button("🔄 전체 새로고침 (F5)"):
        components.html("<script>window.parent.location.reload();</script>", height=0)
        st.stop()

    # [2] 날짜 선택
    available_dates = sorted([d for d in df['날짜_str'].unique() if d and d != "nan"])
    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = available_dates.index(today_str) if today_str in available_dates else 0
    selected_date = st.selectbox("🗓️ 상세 동선 날짜 선택", available_dates, index=default_idx)

    day_df = df[df['날짜_str'] == selected_date].copy().reset_index()

    if not day_df.empty:
        day_df['temp_time_dt'] = pd.to_datetime(day_df['시간'], errors='coerce')
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        current_anchor = None
        if st.session_state.last_lat:
            current_anchor = (st.session_state.last_lat, st.session_state.last_lon)
        else:
            attended_all = day_df[day_df['참석여부'] == '참석'].sort_values('참석시간_dt', ascending=False)
            if not attended_all.empty:
                row = attended_all.iloc[0]
                if not pd.isna(row['위도']): current_anchor = (row['위도'], row['경도'])

        # 리스트 정렬 (시간순 -> 거리순)
        times = sorted(day_df['temp_time_dt'].dropna().unique())
        final_list = []
        for t in times:
            group = day_df[day_df['temp_time_dt'] == t].copy()
            group_att = group[group['참석여부'] == '참석'].sort_values('참석시간_dt')
            group_pending = group[group['참석여부'] == '미체크'].copy()
            if not group_pending.empty and current_anchor:
                # [수정] 위_도 오타 제거 확인 완료
                group_pending['dist'] = group_pending.apply(lambda r: geodesic(current_anchor, (r['위도'], r['경도'])).meters if not pd.isna(r['위도']) else 999999, axis=1)
                group_pending = group_pending.sort_values('dist')
            group_no = group[group['참석여부'] == '불참석']
            final_list.append(pd.concat([group_att, group_pending, group_no]))
        display_df = pd.concat(final_list)

        # [3] 당일 상세 이동 경로 지도
        st.subheader(f"📍 {selected_date} 상세 이동 경로")
        map_df_today = display_df[display_df['위도'].notna() & display_df['경도'].notna()]
        if not map_df_today.empty:
            m_today = folium.Map(location=[map_df_today.iloc[0]['위도'], map_df_today.iloc[0]['경도']], zoom_start=12)
            line_pts = []
            for _, r in map_df_today.iterrows():
                m_color, m_icon = ('blue', 'check') if r['참석여부'] == '참석' else ('gray', 'time') if r['참석여부'] == '미체크' else ('red', 'remove')
                folium.Marker([r['위도'], r['경도']], popup=f"{r['시간']} {r['행사명']}", icon=folium.Icon(color=m_color, icon=m_icon)).add_to(m_today)
                if r['참석여부'] != '불참석': line_pts.append([r['위도'], r['경도']])
            if len(line_pts) > 1: folium.PolyLine(line_pts, color="red", weight=3).add_to(m_today)
            folium_static(m_today)

        # [4] 당일 일정 리스트 (내비 버튼 포함)
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
                        st.session_state.last_lat, st.session_state.last_lon = row['위도'], row['경도']
                        time.sleep(1); st.rerun()
                    if c2.button("🔴 불참석", key=f"no_{orig_idx}"):
                        update_sheet_status(orig_idx, "불참석"); time.sleep(1); st.rerun()
                else:
                    st.write(f"결과: {status}")
                    if st.button("🔄 재선택", key=f"re_{orig_idx}"):
                        update_sheet_status(orig_idx, "미체크"); time.sleep(1); st.rerun()
                # 카카오내비 버튼 유지
                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

    # [5] 참석 횟수 분석 전광판 (맨 하단 배치)
    st.divider()
    st.subheader("📊 지역구별 참석 횟수 현황")
    
    attended_df = df[df['참석여부'] == '참석'].copy()
    if not attended_df.empty:
        attended_df[['지역구', '분류동']] = attended_df.apply(lambda x: pd.Series(get_dong_group(x['주소'])), axis=1)

        sum_tbl = pd.DataFrame({"갑 참석 합계": [len(attended_df[attended_df['지역구'] == "갑"])], 
                                "을 참석 합계": [len(attended_df[attended_df['지역구'] == "을"])]})
        st.table(sum_tbl)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### [영등포구 갑]")
            gap_targets = ["영등포(본)동", "당산1·2동", "도림동", "문래동", "양평1·2동", "신길1·2·3동"]
            gap_data = [{"동네": d, "참석 횟수": len(attended_df[(attended_df['지역구']=="갑") & (attended_df['분류동']==d)])} for d in gap_targets]
            st.table(pd.DataFrame(gap_data))
        with col2:
            st.markdown("#### [영등포구 을]")
            eul_targets = ["여의동", "신길4·5·6·7동", "대림1·2·3동"]
            eul_data = [{"동네": d, "참석 횟수": len(attended_df[(attended_df['지역구']=="을") & (attended_df['분류동']==d)])} for d in eul_targets]
            st.table(pd.DataFrame(eul_data))

except Exception as e:
    st.error(f"오류: {e}")
