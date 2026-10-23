"""Демо-система для трёх производственных участков."""

from datetime import date

import streamlit as st

from calculations import (
    plan_fact_summary,
    validate_blanks,
    validate_documentation,
    validate_welding,
    welding_comparison,
)
from database import get_records, initialize_database, replace_records
from import_data import import_initial_files, initial_import_completed
from reporting import build_csv_report


st.set_page_config(page_title="Панель руководителя", layout="wide")
initialize_database()


PAGES = {
    "Панель директора": "Здесь будут общие показатели, графики и отчёт.",
    "Заготовка": "Здесь сотрудники будут вести план и факт заготовки.",
    "Сварка": "Здесь сотрудники будут вести потребность сварки.",
    "Документация": "Здесь сотрудники будут вести план и факт документации.",
}

WORK_AREAS = {
    "Заготовка": {
        "table": "blanks",
        "validator": validate_blanks,
        "columns": {
            "record_id": "ID записи",
            "date": "Дата",
            "batch_id": "Партия",
            "employee": "Сотрудник",
            "plan_qty": "План, шт.",
            "fact_qty": "Факт, шт.",
        },
    },
    "Сварка": {
        "table": "welding_needs",
        "validator": validate_welding,
        "columns": {
            "record_id": "ID записи",
            "date": "Дата",
            "batch_id": "Партия",
            "need_qty": "Потребность, шт.",
        },
    },
    "Документация": {
        "table": "documentation",
        "validator": validate_documentation,
        "columns": {
            "record_id": "ID записи",
            "date": "Дата",
            "employee": "Сотрудник",
            "plan_docs": "План, док.",
            "fact_docs": "Факт, док.",
        },
    },
}


def render_work_area(area: dict) -> None:
    """Показывает проблемы и форму редактирования одного участка."""
    records = get_records(area["table"])
    checked_records = area["validator"](records)
    problems = [record for record in checked_records if not record["is_valid"]]

    left, right = st.columns(2)
    left.metric("Всего записей", len(records))
    right.metric("Требуют исправления", len(problems))

    if problems:
        st.warning("Проблемные записи не участвуют в достоверных расчётах.")
        st.dataframe(
            [
                {"ID записи": record.get("record_id"), "Проблемы": "; ".join(record["issues"])}
                for record in problems
            ],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.success("Проблем в данных не найдено.")

    labels = area["columns"]
    editor_rows = [
        {label: record.get(column) for column, label in labels.items()}
        for record in records
    ]
    st.subheader("Редактирование данных")
    st.caption("Добавляйте строки кнопкой «Добавить строку». Дату вводите в формате ГГГГ-ММ-ДД.")
    with st.form(f"form_{area['table']}"):
        edited_data = st.data_editor(
            editor_rows,
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            column_config={
                "Дата": st.column_config.TextColumn("Дата (ГГГГ-ММ-ДД)"),
            },
        )
        saved = st.form_submit_button("Сохранить изменения", type="primary")

    if saved:
        edited_rows = (
            edited_data
            if isinstance(edited_data, list)
            else edited_data.to_dict(orient="records")
        )
        edited_records = [
            {column: row.get(label) for column, label in labels.items()}
            for row in edited_rows
        ]
        replace_records(area["table"], edited_records)
        st.success("Изменения сохранены.")
        st.rerun()


def records_in_period(records: list[dict], start: date, end: date) -> list[dict]:
    return [
        record
        for record in records
        if isinstance(record.get("date"), str)
        and start.isoformat() <= record["date"] <= end.isoformat()
    ]


def issue_rows(area_name: str, records: list[dict]) -> list[dict]:
    return [
        {
            "Участок": area_name,
            "Дата": record.get("date"),
            "ID записи": record.get("record_id"),
            "Партия": record.get("batch_id", "—"),
            "Проблемы": "; ".join(record["issues"]),
        }
        for record in records
        if not record["is_valid"]
    ]


def render_director_dashboard() -> None:
    """Показывает сводные показатели и детализацию за выбранный период."""
    raw_blanks = get_records("blanks")
    raw_welding = get_records("welding_needs")
    raw_docs = get_records("documentation")
    all_dates = []
    for record in [*raw_blanks, *raw_welding, *raw_docs]:
        try:
            all_dates.append(date.fromisoformat(record["date"]))
        except (TypeError, ValueError):
            continue
    if not all_dates:
        st.info("Сначала импортируйте исходные данные в боковом меню.")
        return

    start, end = st.date_input(
        "Период отчёта",
        value=(min(all_dates), max(all_dates)),
        format="DD.MM.YYYY",
    )
    blanks = validate_blanks(records_in_period(raw_blanks, start, end))
    welding = validate_welding(records_in_period(raw_welding, start, end))
    docs = validate_documentation(records_in_period(raw_docs, start, end))
    blank_summary = plan_fact_summary(blanks, "plan_qty", "fact_qty")
    docs_summary = plan_fact_summary(docs, "plan_docs", "fact_docs")
    welding_rows = welding_comparison(blanks, welding)
    confirmed_welding = [row for row in welding_rows if row["is_valid"]]
    linked_welding_issues = len(welding_rows) - len(confirmed_welding)

    st.subheader("Основные показатели")
    blank_kpi, welding_kpi, docs_kpi = st.columns(3)
    blank_kpi.metric(
        "Заготовка: факт / план",
        f"{blank_summary['fact']:g} / {blank_summary['plan']:g}",
        f"{blank_summary['completion']:.1%}" if blank_summary["completion"] is not None else "—",
    )
    welding_kpi.metric(
        "Сварка: подтверждённый баланс",
        f"{sum(row['balance_qty'] for row in confirmed_welding):g} шт.",
        f"партий на проверке: {linked_welding_issues}",
        delta_color="off",
    )
    docs_kpi.metric(
        "Документация: факт / план",
        f"{docs_summary['fact']:g} / {docs_summary['plan']:g}",
        f"{docs_summary['completion']:.1%}" if docs_summary["completion"] is not None else "—",
    )
    if blank_summary["invalid_records"] or docs_summary["invalid_records"] or linked_welding_issues:
        st.warning(
            "В периоде есть данные, требующие проверки: "
            f"заготовка — {blank_summary['invalid_records']}, "
            f"документация — {docs_summary['invalid_records']}, "
            f"связанные партии сварки — {linked_welding_issues}."
        )

    daily_rows = []
    period_dates = sorted({record["date"] for record in [*blanks, *welding, *docs]})
    for day in period_dates:
        day_blanks = [record for record in blanks if record["date"] == day]
        day_docs = [record for record in docs if record["date"] == day]
        day_welding = [record for record in welding if record["date"] == day]
        daily_rows.append(
            {
                "Дата": day,
                "Заготовка: план": sum(record["plan_qty"] for record in day_blanks if record["is_valid"]),
                "Заготовка: факт": sum(record["fact_qty"] for record in day_blanks if record["is_valid"]),
                "Сварка: потребность": sum(record["need_qty"] for record in day_welding if record["is_valid"]),
                "Документация: план": sum(record["plan_docs"] for record in day_docs if record["is_valid"]),
                "Документация: факт": sum(record["fact_docs"] for record in day_docs if record["is_valid"]),
            }
        )

    st.subheader("Динамика")
    if daily_rows:
        chart_left, chart_right = st.columns(2)
        chart_left.bar_chart(daily_rows, x="Дата", y=["Заготовка: план", "Заготовка: факт"])
        chart_right.bar_chart(daily_rows, x="Дата", y=["Документация: план", "Документация: факт"])
        st.subheader("Сводная таблица по дням")
        st.dataframe(daily_rows, hide_index=True, use_container_width=True)
    else:
        st.info("За выбранный период нет записей для построения графиков и сводной таблицы.")

    with st.expander("Сварка: детализация по партиям", expanded=True):
        st.dataframe(
            [
                {
                    "Партия": row["batch_id"],
                    "Потребность": row["need_qty"],
                    "Факт заготовки": row["blank_fact_qty"],
                    "Баланс": row["balance_qty"],
                    "Статус": "Корректно" if row["is_valid"] else "; ".join(row["issues"]),
                }
                for row in welding_rows
            ],
            hide_index=True,
            use_container_width=True,
        )

    problems = [
        *issue_rows("Заготовка", blanks),
        *issue_rows("Сварка", welding),
        *issue_rows("Документация", docs),
    ]
    report = build_csv_report(
        start.isoformat(), end.isoformat(), blank_summary, docs_summary,
        welding_rows, daily_rows, problems,
    )
    st.download_button(
        "Скачать отчёт CSV",
        data=report.encode("utf-8-sig"),
        file_name=f"report_{start.isoformat()}_{end.isoformat()}.csv",
        mime="text/csv",
        type="primary",
    )
    with st.expander("Проблемные исходные записи"):
        if problems:
            st.dataframe(problems, hide_index=True, use_container_width=True)
        else:
            st.success("В выбранном периоде проблемных исходных записей нет.")

    with st.expander("Все исходные записи периода"):
        for title, records in (("Заготовка", blanks), ("Сварка", welding), ("Документация", docs)):
            st.markdown(f"**{title}**")
            st.dataframe(
                [
                    {key: value for key, value in record.items() if key not in {"id", "source_row", "issues", "is_valid"}}
                    for record in records
                ],
                hide_index=True,
                use_container_width=True,
            )


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
st.caption(PAGES[selected_page])

if selected_page == "Панель директора":
    render_director_dashboard()
else:
    render_work_area(WORK_AREAS[selected_page])
