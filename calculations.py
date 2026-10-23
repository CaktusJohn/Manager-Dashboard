"""Проверки качества данных и расчёт показателей."""

from collections import Counter, defaultdict
from typing import Any


def _is_positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _duplicate_ids(records: list[dict]) -> set[str]:
    ids = [record.get("record_id") for record in records if record.get("record_id")]
    return {record_id for record_id, count in Counter(ids).items() if count > 1}


def _base_issues(record: dict, duplicate_ids: set[str], required_fields: tuple[str, ...]) -> list[str]:
    issues = []
    for field in required_fields:
        if record.get(field) in (None, ""):
            issues.append(f"Не заполнено поле «{field}»")
    if record.get("record_id") in duplicate_ids:
        issues.append("Повторяющийся record_id")
    return issues


def validate_blanks(records: list[dict]) -> list[dict]:
    """Проверяет выпуск заготовок. Выброс — факт более чем вдвое выше плана."""
    duplicate_ids = _duplicate_ids(records)
    result = []
    for record in records:
        issues = _base_issues(
            record, duplicate_ids, ("record_id", "date", "batch_id", "employee", "plan_qty", "fact_qty")
        )
        plan, fact = record.get("plan_qty"), record.get("fact_qty")
        if plan not in (None, "") and not _is_positive(plan):
            issues.append("План должен быть больше нуля")
        if fact not in (None, "") and (not _is_number(fact) or fact < 0):
            issues.append("Факт не может быть отрицательным")
        if _is_positive(plan) and _is_number(fact) and fact > plan * 2:
            issues.append("Подозрительный факт: более чем в 2 раза выше плана")
        result.append({**record, "issues": issues, "is_valid": not issues})
    return result


def validate_welding(records: list[dict]) -> list[dict]:
    """Проверяет потребность сварки, независимую от факта заготовки."""
    duplicate_ids = _duplicate_ids(records)
    result = []
    for record in records:
        issues = _base_issues(record, duplicate_ids, ("record_id", "date", "batch_id", "need_qty"))
        need = record.get("need_qty")
        if need not in (None, "") and not _is_positive(need):
            issues.append("Потребность должна быть больше нуля")
        result.append({**record, "issues": issues, "is_valid": not issues})
    return result


def validate_documentation(records: list[dict]) -> list[dict]:
    """Проверяет план и факт документации."""
    duplicate_ids = _duplicate_ids(records)
    result = []
    for record in records:
        issues = _base_issues(
            record, duplicate_ids, ("record_id", "date", "employee", "plan_docs", "fact_docs")
        )
        plan, fact = record.get("plan_docs"), record.get("fact_docs")
        if plan not in (None, "") and not _is_positive(plan):
            issues.append("План должен быть больше нуля")
        if fact not in (None, "") and (not _is_number(fact) or fact < 0):
            issues.append("Факт не может быть отрицательным")
        if _is_positive(plan) and _is_number(fact) and fact > plan * 2:
            issues.append("Подозрительный факт: более чем в 2 раза выше плана")
        result.append({**record, "issues": issues, "is_valid": not issues})
    return result


def plan_fact_summary(records: list[dict], plan_field: str, fact_field: str) -> dict:
    """Считает KPI только по корректным строкам и сообщает об исключённых."""
    valid_records = [record for record in records if record["is_valid"]]
    plan = sum(record[plan_field] for record in valid_records)
    fact = sum(record[fact_field] for record in valid_records)
    return {
        "plan": plan,
        "fact": fact,
        "completion": fact / plan if plan else None,
        "valid_records": len(valid_records),
        "invalid_records": len(records) - len(valid_records),
    }


def welding_comparison(
    blanks: list[dict], welding_needs: list[dict]
) -> list[dict]:
    """Сопоставляет факт заготовки с потребностью сварки по партии.

    Если хоть одна строка заготовки партии сомнительна, показатель сварки не
    рассчитывается как достоверный.
    """
    blanks_by_batch: dict[str, list[dict]] = defaultdict(list)
    needs_by_batch: dict[str, list[dict]] = defaultdict(list)
    for record in blanks:
        blanks_by_batch[record.get("batch_id")].append(record)
    for record in welding_needs:
        needs_by_batch[record.get("batch_id")].append(record)

    comparison = []
    for batch_id, need_records in needs_by_batch.items():
        issues = [issue for record in need_records for issue in record["issues"]]
        blank_records = blanks_by_batch.get(batch_id, [])
        if not blank_records:
            issues.append("Нет факта заготовки по партии")
        elif any(not record["is_valid"] for record in blank_records):
            issues.append("Факт заготовки по партии требует исправления")

        need_qty = sum(record["need_qty"] for record in need_records if record["is_valid"])
        fact_qty = (
            sum(record["fact_qty"] for record in blank_records)
            if blank_records and not any(not record["is_valid"] for record in blank_records)
            else None
        )
        comparison.append(
            {
                "batch_id": batch_id,
                "need_qty": need_qty if not issues else None,
                "blank_fact_qty": fact_qty,
                "balance_qty": fact_qty - need_qty if not issues else None,
                "issues": issues,
                "is_valid": not issues,
            }
        )
    return sorted(comparison, key=lambda row: row["batch_id"] or "")
