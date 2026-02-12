import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from geopy.distance import geodesic

# 1. 설정 정보 (사무장님이 주신 새 주소 적용 완료)
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"
script_url = "https://script.google.com/macros/s/AKfycbzlPtAOqvz0wSgbspGz9PbZuDcdd-BBtbbep_uEtCFTaBd4vYG5Pu6jo0dkESkVBIgI/exec"

KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)

st.set_page_config(page_title="최웅식 캠프 실시간 보고", layout="centered")

# 시트 기록 함수 (참석/불참석)
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

# CSS 설정
st.markdown("""<style> div.stButton > button { width: 100% !important; height: 50px !important; } </style>""", unsafe_allow_html=True)

st.title("🚩 최웅식 캠프 실시간 동선")

try:
    # 1. 데이터 불러오기
    df = pd.read_csv(f"{sheet_url}&t={now_kst.timestamp()}")
    df = df.fillna("")
    
    # 좌표 데이터를 숫자로 변환
    df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
    df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    df['temp_time'] = pd.to_datetime(df['시간'], errors='coerce').dt.time
    
    # 날짜 선택
    available_dates = sorted(df['날짜_dt'].unique())
    today_val = now_kst.date()
    default_idx = list(available_dates).index(today_val) if today_val in available_dates else 0
    selected_date = st.selectbox("🗓️ 날짜 선택", available_dates, index=default_idx)
    
    if st.button("🔄 데이터 새로고침"): st.rerun()
    st.divider()

    # 선택한 날짜의 데이터만 필터링
    day_df = df[df['날짜_dt'] == selected_date].copy().reset_index()
    
    if not day_df.empty:
        # --- [계단식 동선 정렬 알고리즘] ---
        times = sorted(day_df['temp_time'].unique())
        final_list = []
        
        # 기준점 설정 로직
        # 1순위: 가장 마지막으로 '참석'을 누른 장소
        # 2순위: 아무것도 없으면 앞 시간대 1등 장소
        attended_events = day_df[day_df['참석여부'] == '참석'].sort_values('temp_time')
        last_ref_coords = None
        base_name = "오늘의 시작"

        if not attended_events.empty:
            last_att = attended_events.iloc[-1]
            if not pd.isna(last_att['위도']):
                last_ref_coords = (last_att['위도'], last_att['경도'])
                base_name = f"마지막 참석지: {last_att['행사명']}"

        st.info(f"📍 현재 기준점: **{base_name}**")

        for t in times:
            group = day_df[day_df['temp_time'] == t].copy()
            
            # 이미 결과가 나온(참석/불참석) 행은 정렬하지 않음
            if (group['참석여부'].isin(['참석', '불참석'])).any():
                final_list.append(group)
                # 이 그룹에 참석이 있다면 기준점 업데이트
                att_row = group[group['참석여부'] == '참석']
                if not att_row.empty and not pd.isna(att_row.iloc[-1]['위도']):
                    last_ref_coords = (att_row.iloc[-1]['위도'], att_row.iloc[-1]['경도'])
            else:
                # 미체크 상태면 거리순 정렬
                if last_ref_coords:
                    def get_d(row):
                        if pd.isna(row['위도']): return 999999
                        return geodesic(last_ref_coords, (row['위도'], row['경도'])).meters
                    
                    group['dist'] = group.apply(get_d, axis=1)
                    group = group.sort_values('dist')
                
                final_list.append(group)
                # 다음 시간대를 위해 이 시간대의 1등을 기준점으로 갱신
                if not group.empty and not pd.isna(group.iloc[0]['위도']):
                    last_ref_coords = (group.iloc[0]['위도'], group.iloc[0]['경도'])

        display_df = pd.concat(final_list)

        # 2. 결과 출력
        for _, row in display_df.iterrows():
            orig_idx = row['index']
            with st.container(border=True):
                status = str(row.get('참석여부', '')).strip()
                if status not in ["참석", "불참석"]: status = "미체크"
                
                title_icon = "✅" if status == "참석" else "❌" if status == "불참석" else "⏱️"
                st.markdown(f"### {title_icon} {row['시간']} | {row['행사명']}")
                st.caption(f"📍 {row['주소']}")
                
                if pd.isna(row['위도']):
                    st.warning("⚠️ 시트에서 '좌표 변환' 버튼을 눌러주세요.")

                if status == "미체크":
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🟢 참석", key=f"at_{orig_idx}"):
                            if update_sheet_status(orig_idx, "참석"): st.rerun()
                    with c2:
                        if st.button("🔴 불참석", key=f"no_{orig_idx}"):
                            if update_sheet_status(orig_idx, "불참석"): st.rerun()
                else:
                    st.success(f"결과: {status}")
                    if st.button("🔄 상태 수정", key=f"ed_{orig_idx}"):
                        if update_sheet_status(orig_idx, "미체크"): st.rerun()

                st.link_button("🚕 카카오내비 실행", f"https://map.kakao.com/link/search/{urllib.parse.quote(str(row['주소']))}")
    else:
        st.warning("등록된 일정이 없습니다.")

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")
