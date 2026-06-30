import streamlit as st

st.set_page_config(
    page_title="RG25 - Sinner vs Alcaraz",
    page_icon="🎾",
    layout="wide",
)

# Explicitly define the sidebar navigation
pages = [
    st.Page("pages/1_Overview.py", title="Overview", icon="🏠"),
    st.Page("pages/2_Line_Chart.py", title="Line Chart", icon="📈"),
    st.Page("pages/3_Radar_Chart.py", title="Radar Chart", icon="🕸️"),
    st.Page("pages/4_Court_Chart.py", title="Court Chart", icon="🎾"),
]

pg = st.navigation(pages)
pg.run()