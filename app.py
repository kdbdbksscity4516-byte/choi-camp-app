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

st.set_page_config(
    page_title="최웅식 후보 동선 관리", 
    layout="wide",
    page_icon="https://github.com/kdbdbksscity4516-byte/choi-camp-app/raw/main/icon.png?v=2"
)

if 'last_lat' not in st.session_state: st.session_state.last_lat = None
if 'last_lon' not in st.session_state: st.session_state.last_lon = None

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
    
    # [추가] 우선순위 숫자 변환 (비어있으면 아주 큰 숫자 999 부여해서 뒤로 보냄)
    if '우선순위' in df.columns:
        df['우선순위'] = pd.to_numeric(df['우선순위'], errors='coerce').fillna(999)
    else:
        df['우선순위'] = 999
        
    df['날짜_str'] = df['날짜'].astype(str).str.strip()

    # 사진 주소 갱신용 (?v=1)
    raw_img_url = "https://github.com/kdbdbksscity4516-byte/choi-camp-app/raw/main/banner.png?v=1"
    st.image(raw_img_url, use_container_width=True)

    st.title("최웅식 후보 동선 최적화 & 활동 분석")

    if st.button("🔄 전체 새로고침 (F5)"):
        components.html("<script>window.parent.location.reload();</script>", height=0)
        st.stop()

    # --- [금일 일정 요약 - 우선순위 반영 정렬] ---
    today_str_check = now_kst.strftime('%Y-%m-%d')
    today_summary_df = df[df['날짜_str'] == today_str_check].copy()
    
    with st.expander("📅 금일 전체 일정 요약 (수행자 클릭 시 전화연결)", expanded=True):
        if not today_summary_df.empty:
            today_summary_df['temp_time'] = pd.to_datetime(today_summary_df['시간'], errors='coerce')
            # 정렬 순서: 우선순위(작은순) -> 시간(빠른순)
            summary_list = today_summary_df.sort_values(['우선순위', 'temp_time'])
            
            for _, row in summary_list.iterrows():
                status_icon = "⚪"
                if row['참석여부'] == "참석": status_icon = "🔵"
                elif row['참석여부'] == "불참석": status_icon = "🔴"
                
                person = str(row['수행자']).strip() if '수행자' in row and row['수행자'] != "" else "담당자미정"
                phone = str(row['수행자전화번호']).strip() if '수행자전화번호' in row and row['수행자전화번호'] != "" else ""
                
                time_range = f"{row['시간']} ~ {row['종료시간']}" if '종료시간' in row and str(row['종료시간']).strip() != "" else row['시간']
                
                if phone:
                    clean_phone = phone.replace("-", "")
                    contact_html = f"<a href='tel:{clean_phone}' target='_self' style='color: #007bff; text-decoration: underline; font-weight: bold;'>{person}</a>"
                    st.markdown(f"{status_icon} **{time_range}** | {row['행사명']} ({contact_html})", unsafe_allow_html=True)
                else:
                    st.markdown(f"{status_icon} **{time_range}** | {row['행사명']} ({person})")
        else:
            st.write("오늘 예정된 일정이 없습니다.")

    available_dates = sorted([d for d in df['날짜_str'].unique() if d and d != "nan"])
    today_str = now_kst.strftime('%Y-%m-%d')
    default_idx = available_dates.index(today_str) if today_str in available_dates else 0
    selected_date = st.selectbox("🗓️ 상세 동선 날짜 선택", available_dates, index=default_idx)

    day_df = df[df['날짜_str'] == selected_date].copy().reset_index()

    if not day_df.empty:
        day_df['temp_time_dt'] = pd.to_datetime(day_df['시간'], errors='coerce')
        # [수정] 상세 리스트도 우선순위와 시간을 함께 고려하여 정렬
        display_df = day_df.sort_values(['우선순위', 'temp_time_dt']).copy()

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
            folium_static(m_today, width=None, height=350)

        # 📝 상세 활동 리스트 (우선순위 정렬 반영)
        st.subheader("📝 상세 활동 리스트")
        for _, row in display_df.iterrows():
            orig_idx = row['index']
            with st.container(border=True):
                display_time = f"{row['시간']} ~ {row['종료시간']}" if '종료시간' in row and str(row['종료시간']).strip() != "" else row['시간']
                st.markdown(f"### {display_time} | {row['행사명']}")
                
                address_val = str(row['주소']).strip() if '주소' in row and row['주소'] != "" else "주소 정보 없음"
                st.write(f"📍 **주소:** {address_val}")
                
                detail_address = str(row['상세주소']).strip() if '상세주소' in row and row['상세주소'] != "" else ""
                if detail_address:
                    st.write(f"🏢 **상세주소:** {detail_address}")
                
                person_label = str(row['수행자']).strip() if '수행자' in row and row['수행자'] != "" else "담당자미정"
                st.write(f"👤 **수행자:** {person_label}")
                
                status = str(row['참석여부']).strip()
                if status == "미체크":
                    c1, c2 = st.columns(2)
                    if c1.button("🟢 참석", key=f"at_{orig_idx}"):
                        update_sheet_status(orig_idx, "참석"); time.sleep(1); st.rerun()
                    if c2.button("🔴 불참석", key=f"no_{orig_idx}"):
                        update_sheet_status(orig_idx, "불참석"); time.sleep(1); st.rerun()
                else:
                    st.success(f"결과: {status}")
                    if st.button("🔄 재선택", key=f"re_at_{orig_idx}"): update_sheet_status(orig_idx, "미체크"); time.sleep(1); st.rerun()
                st.link_button("🚕 카카오내비", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")

    # 📊 누적 분석 지도
    st.divider()
    st.subheader("📊 선거 운동 누적 활동 분석")
    all_map_df = df[df['참석여부'].isin(['참석', '불참석'])]
    all_map_df = all_map_df[all_map_df['위도'].notna() & all_map_df['경도'].notna()]
    if not all_map_df.empty:
        center_lat = all_map_df['위도'].mean()
        center_lon = all_map_df['경도'].mean()
        m_all = folium.Map(location=[center_lat, center_lon], zoom_start=11)
        for _, r in all_map_df.iterrows():
            m_color, m_icon = ('blue', 'check') if r['참석여부'] == '참석' else ('red', 'remove')
            folium.Marker([r['위도'], r['경도']], icon=folium.Icon(color=m_color, icon=m_icon)).add_to(m_all)
    else:
        m_all = folium.Map(location=[37.5665, 126.9780], zoom_start=11)
        st.info("아직 누적 기록이 없습니다.")
    folium_static(m_all, width=None, height=250)

except Exception as e:
    st.error(f"오류 발생: {e}")
