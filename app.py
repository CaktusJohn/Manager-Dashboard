"""Демо-система для трёх производственных участков."""

import streamlit as st

from database import initialize_database


st.set_page_config(page_title="Панель руководителя", page_icon="📊", layout="wide")
initialize_database()


PAGES = {
    "Панель директора": "Здесь будут общие показатели, графики и отчёт.",
    "Заготовка": "Здесь сотрудники будут вести план и факт заготовки.",
    "Сварка": "Здесь сотрудники будут вести потребность сварки.",
    "Документация": "Здесь сотрудники будут вести план и факт документации.",
}


with st.sidebar:
    st.title("Производство")
    selected_page = st.radio("Раздел", list(PAGES), label_visibility="collapsed")

st.title(selected_page)
st.info(PAGES[selected_page])

if selected_page == "Панель директора":
    st.caption("Данные будут загружены из исходных Excel-файлов на следующем этапе.")
