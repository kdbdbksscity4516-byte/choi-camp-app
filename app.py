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
    df['날짜_str'] = df['날짜'].astype(str).str.strip()

    raw_img_url = "https://github.com/kdbdbksscity4516-byte/choi-camp-app/raw/main/banner.png"
    st.image(raw_img_url, use_container_width=True)

    st.title("최웅식 후보 동선 최적화 & 활동 분석")

    if st.button("🔄 전체 새로고침 (F5)"):
        components.html("<script>window.parent.location.reload();</script>", height=0)
        st.stop()

    # --- [금일 일정 요약] ---
    today_str_check = now_kst.strftime('%Y-%m-%d')
    today_summary_df = df[df['날짜_str'] == today_str_check].copy()
    
    with st.expander("📅 금일 전체 일정 요약 (수행자 클릭 시 전화연결)", expanded=True):
        if not today_summary_df.empty:
            today_summary_df['temp_time'] = pd.to_datetime(today_summary_df['시간'], errors='coerce')
            summary_list = today_summary_df.sort_values('temp_time')
            
            for _, row in summary_list.iterrows():
                status_icon = "⚪"
                if row['참석여부'] == "참석": status_icon = "🔵"
                elif row['참석여부'] == "불참석": status_icon = "🔴"
                
                person = str(row['수행자']).strip() if '수행자' in row and row['수행자'] != "" else "담당자미정"
                phone = str(row['수행자전화번호']).strip() if '수행자전화번호' in row and row['수행자전화번호'] != "" else ""
                
                # 시간 표시 (요약본)
                time_range = f"{row['시간']} ~ {row['종료시간']}" if '종료시간' in row and row['종료시간'] != "" else row['시간']
                
                if phone:
                    clean_phone = phone.replace("-", "")
                    contact_html = f"<a href='tel:{clean_phone}' style='color: #007bff; text-decoration: underline; font-weight: bold;'>{person}</a>"
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
        day_df['참석시간_dt'] = pd.to_datetime(day_df['참석시간'], errors='coerce')
        
        times = sorted(day_df['temp_time_dt'].dropna().unique())
        final_list = []
        current_anchor = None

        for t in times:
            group = day_df[day_df['temp_time_dt'] == t].copy()
            group_att = group[group['참석여부'] == '참석'].sort_values('참석시간_dt')
            if not group_att.empty:
                last_att = group_att.iloc[-1]
                if not pd.isna(last_att['위도']):
                    current_anchor = (last_att['위도'], last_att['경도'])
            
            group_pending = group[group['참석여부'] == '미체크'].copy()
            if not group_pending.empty:
                if current_anchor is None:
                    first_row = group_pending.iloc[0]
                    if not pd.isna(first_row['위도']):
                        current_anchor = (first_row['위도'], first_row['경도'])
                
                if current_anchor:
                    group_pending['dist'] = group_pending.apply(lambda r: geodesic(current_anchor, (r['위도'], r['경도'])).meters if not pd.isna(r['위도']) else 999999, axis=1)
                    group_pending = group_pending.sort_values('dist')
                
                last_pending = group_pending.iloc[-1]
                if not pd.isna(last_pending['위도']):
                    current_anchor = (last_pending['위도'], last_pending['경도'])
            
            group_no = group[group['참석여부'] == '불참석']
            final_list.append(pd.concat([group_att, group_pending, group_no]))

        display_df = pd.concat(final_list)

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

        # 📝 [종료시간 반영] 상세 활동 리스트
        st.subheader("📝 상세 활동 리스트")
        for _, row in display_df.iterrows():
            orig_idx = row['index']
            with st.container(border=True):
                # 제목 영역에 종료 시간까지 표시
                display_time = f"{row['시간']} ~ {row['종료시간']}" if '종료시간' in row and row['종료시간'] != "" else row['시간']
                st.markdown(f"### {display_time} | {row['행사명']}")
                
                # 주소 정보
                address_val = str(row['주소']).strip() if '주소' in row and row['주소'] != "" else "주소 정보 없음"
                st.write(f"📍 **주소:** {address_val}")
                
                # 수행자 정보
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
        m_all = folium.Map(location=[all_map_df['위도'].mean(), all_map_df['경도'].mean()], zoom_start=11)
        for _, r in all_map_df.iterrows():
            m_color, m_icon = ('blue', 'check') if r['참석여부'] == '참석' else ('red', 'remove')
            folium.Marker([r['위도'], r['경도']], icon=folium.Icon(color=m_color, icon=m_icon)).add_to(m_all)
    else:
        m_all = folium.Map(location=[37.5665, 126.9780], zoom_start=11)
        st.info("아직 누적 기록이 없습니다.")
    folium_static(m_all, width=None, height=250)

except Exception as e:
    st.error(f"오류: {e}")
