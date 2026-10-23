"""Демо-система для трёх производственных участков."""

import streamlit as st

from database import initialize_database
from import_data import import_initial_files, initial_import_completed


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
    st.divider()
    if initial_import_completed():
        st.success("Исходные данные загружены в базу")
    else:
        st.caption("Первоначальная загрузка")
        blanks_file = st.file_uploader("Файл «Заготовка»", type="xlsx")
        welding_file = st.file_uploader("Файл «Потребность сварки»", type="xlsx")
        documentation_file = st.file_uploader("Файл «Документация»", type="xlsx")

    import_clicked = (
        not initial_import_completed()
        and st.button("Импортировать данные", use_container_width=True)
    )

    if import_clicked:
        try:
            with st.spinner("Загружаем данные в локальную базу..."):
                counts = import_initial_files(
                    {
                        "blanks": blanks_file,
                        "welding_needs": welding_file,
                        "documentation": documentation_file,
                    }
                )
            st.success(
                "Загружено: "
                f"заготовка — {counts['blanks']}, "
                f"сварка — {counts['welding_needs']}, "
                f"документация — {counts['documentation']}"
            )
            st.rerun()
        except ValueError as error:
            st.error(str(error))

st.title(selected_page)
st.info(PAGES[selected_page])

if selected_page == "Панель директора":
    st.caption("Данные будут загружены из исходных Excel-файлов на следующем этапе.")
