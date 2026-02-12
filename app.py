import streamlit as st
import pandas as pd

# 사무장님의 구글 시트 주소
sheet_url = "https://docs.google.com/spreadsheets/d/1XsTB4nUPL03xba1cEGYGUsyNZcmsdFEGEU2S-6DfpL4/export?format=csv"

st.set_page_config(page_title="최웅식 캠프 동선공유", layout="centered")

st.title("🚩 최웅식 캠프 동선공유")
st.info("구글 시트의 내용이 실시간으로 반영됩니다.")

try:
    df = pd.read_csv(sheet_url)
    # 데이터가 있으면 시간순 정렬
    if not df.empty:
        df = df.sort_values(by=['날짜', '시간'])
        
        for idx, row in df.iterrows():
            with st.container():
                col1, col2 = st.columns([1, 4])
                col1.metric("시간", str(row['시간']))
                with col2:
                    st.subheader(f"{row['행사명']}")
                    st.write(f"📍 {row['주소']}")
                    if pd.notna(row['비고']):
                        st.caption(f"💬 {row['비고']}")
                st.divider()

        # 전체 동선 지도보기 버튼
        addr_list = "/".join([str(a) for a in df['주소'] if pd.notna(a)])
        if addr_list:
            map_url = f"https://www.google.com/maps/dir/{addr_list}"
            st.link_button("🚗 전체 동선 선 연결 지도보기", map_url, use_container_width=True)
    else:
        st.warning("시트에 데이터가 없습니다. 내용을 입력해주세요.")

except Exception as e:
    st.error("데이터를 불러오는 중입니다. 잠시만 기다려주시거나 시트 공유 설정을 확인해주세요.")
