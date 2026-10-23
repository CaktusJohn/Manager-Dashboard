"""Создание простого CSV-отчёта для панели директора."""

import csv
from io import StringIO


def _value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def build_csv_report(
    start: str,
    end: str,
    blank_summary: dict,
    docs_summary: dict,
    welding_rows: list[dict],
    daily_rows: list[dict],
    problems: list[dict],
) -> str:
    """Возвращает единый CSV с разделами, пригодный для открытия в Excel."""
    confirmed_welding = [row for row in welding_rows if row["is_valid"]]
    welding_need = sum(row["need_qty"] for row in confirmed_welding)
    welding_fact = sum(row["blank_fact_qty"] for row in confirmed_welding)
    welding_balance = sum(row["balance_qty"] for row in confirmed_welding)

    output = StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Отчёт панели руководителя"])
    writer.writerow(["Период", start, end])
    writer.writerow([])
    writer.writerow(["Основные показатели"])
    writer.writerow(["Участок", "План / потребность", "Факт", "Выполнение / баланс", "Требует проверки"])
    writer.writerow([
        "Заготовка", _value(blank_summary["plan"]), _value(blank_summary["fact"]),
        f"{blank_summary['completion']:.1%}" if blank_summary["completion"] is not None else "",
        blank_summary["invalid_records"],
    ])
    writer.writerow([
        "Сварка (подтверждённые партии)", _value(welding_need), _value(welding_fact),
        _value(welding_balance), len(welding_rows) - len(confirmed_welding),
    ])
    writer.writerow([
        "Документация", _value(docs_summary["plan"]), _value(docs_summary["fact"]),
        f"{docs_summary['completion']:.1%}" if docs_summary["completion"] is not None else "",
        docs_summary["invalid_records"],
    ])
    writer.writerow([])

    writer.writerow(["Сводка по дням"])
    if daily_rows:
        writer.writerow(daily_rows[0].keys())
        writer.writerows(row.values() for row in daily_rows)
    writer.writerow([])

    writer.writerow(["Сварка по партиям"])
    writer.writerow(["Партия", "Потребность", "Факт заготовки", "Баланс", "Статус"])
    for row in welding_rows:
        writer.writerow([
            row["batch_id"], _value(row["need_qty"]), _value(row["blank_fact_qty"]),
            _value(row["balance_qty"]),
            "Корректно" if row["is_valid"] else "; ".join(row["issues"]),
        ])
    writer.writerow([])

    writer.writerow(["Проблемные исходные записи"])
    writer.writerow(["Участок", "Дата", "ID записи", "Партия", "Проблемы"])
    for problem in problems:
        writer.writerow(problem.values())
    return output.getvalue()
