#!/usr/bin/env python3 """Расчёт количества заказов и выручки по артикулам и датам."""
import argparse 
import csv 
from collections import defaultdict 
from datetime import date 
from decimal import Decimal, InvalidOperation 
from pathlib import Path

DELIVERED = "delivered" 
CANCELLED = "cancelled"

STATUS_ALIASES = { 
    "delivered": DELIVERED, 
    "cancelled": CANCELLED, 
    "canceled": CANCELLED, 
}

REQUIRED_COLUMNS = { 
    "order_id", 
    "order_date",
    "sku", 
    "quantity", 
    "price", 
    "status", 
}

def parse_decimal(value, field, row_number, allow_empty=False): 
    """Преобразует значение в число.""" 
    value = (value or "").strip()
    if not value and allow_empty:
        return None

    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(
            f"Строка {row_number}: некорректное значение "
            f"{field}={value!r}"
        ) from exc
    
def calculate(input_path): 
    """Считает уникальные заказы и выручку по SKU и дате."""
    aggregates = defaultdict(lambda: [0, Decimal("0")])
    seen_orders = {}

    with Path(input_path).open(
        "r", encoding="utf-8-sig", newline=""
    ) as source:

        reader = csv.DictReader(source)

        if (
            not reader.fieldnames
            or not REQUIRED_COLUMNS.issubset(reader.fieldnames)
        ):
            raise ValueError(
                "В CSV отсутствуют обязательные колонки: "
                + ", ".join(sorted(REQUIRED_COLUMNS))
            )

        for row_number, row in enumerate(reader, start=2):

            order_id = (row.get("order_id") or "").strip()
            order_date = (row.get("order_date") or "").strip()
            sku = (row.get("sku") or "").strip()

            raw_status = (
                (row.get("status") or "").strip().lower()
            )

            if not order_id or not order_date or not sku:
                raise ValueError(
                    f"Строка {row_number}: пустой order_id, "
                    "order_date или sku"
                )

            try:
                date.fromisoformat(order_date)
            except ValueError as exc:
                raise ValueError(
                    f"Строка {row_number}: "
                    f"некорректная дата {order_date!r}"
                ) from exc

            if raw_status not in STATUS_ALIASES:
                raise ValueError(
                    f"Строка {row_number}: "
                    f"неизвестный статус {raw_status!r}"
                )

            status = STATUS_ALIASES[raw_status]

            raw_quantity = (row.get("quantity") or "").strip()

            if not raw_quantity and status == DELIVERED:
                raise ValueError(
                    f"Строка {row_number}: у выкупленного "
                    "заказа отсутствует quantity"
                )

            quantity = parse_decimal(
                row.get("quantity"),
                "quantity",
                row_number,
                allow_empty=(status == CANCELLED),
            )

            price = parse_decimal(
                row.get("price"),
                "price",
                row_number,
            )

            if price < 0 or (
                quantity is not None and quantity < 0
            ):
                raise ValueError(
                    f"Строка {row_number}: цена и количество "
                    "не могут быть отрицательными"
                )

            # Проверяем, не встречался ли заказ ранее.
            signature = (
                order_date,
                sku,
                quantity,
                price,
                status,
            )

            if order_id in seen_orders:
                if seen_orders[order_id] != signature:
                    raise ValueError(
                        f"Заказ {order_id} встречается "
                        "с разными данными. Нужна ручная проверка."
                    )

                continue

            seen_orders[order_id] = signature

            key = (sku, order_date)

            # Каждый уникальный заказ учитывается один раз.
            aggregates[key][0] += 1

            # Выручка рассчитывается только для delivered.
            if status == DELIVERED:
                aggregates[key][1] += quantity * price

    return aggregates

def write_report(aggregates, output_path): 
    """Сохраняет итоговую таблицу в CSV."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline=""
    ) as target:

        writer = csv.writer(target, lineterminator="\n")

        writer.writerow([
            "sku",
            "order_date",
            "orders",
            "revenue",
        ])

        for (sku, order_date), (orders, revenue) in sorted(
            aggregates.items()
        ):

            revenue_text = format(revenue, "f")

            if "." in revenue_text:
                revenue_text = (
                    revenue_text.rstrip("0").rstrip(".")
                )

            writer.writerow([
                sku,
                order_date,
                orders,
                revenue_text,
            ])
def main(): 
    parser = argparse.ArgumentParser( description="Расчёт продаж по артикулам и датам" )
    parser.add_argument(
            "--input",
            default="sales.csv",
            help="Путь к исходному CSV",
    )

    parser.add_argument(
        "--output",
        default="daily_by_sku.csv",
        help="Путь к итоговому CSV",
    )

    args = parser.parse_args()

    aggregates = calculate(args.input)

    with open(args.input, "r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        input_rows = sum(1 for row in reader)

    unique_orders = sum(values[0] for values in aggregates.values())
    total_revenue = sum(
        (values[1] for values in aggregates.values()),
        Decimal("0")
    )
    dates = {order_date for sku, order_date in aggregates}
    skus = {sku for sku, order_date in aggregates}

    write_report(aggregates, args.output)

    print("\nОбработка завершена успешно!")
    print(f"Входных строк: {input_rows}")
    print(f"Уникальных заказов: {unique_orders}")
    print(f"Количество дат: {len(dates)}")
    print(f"Количество SKU: {len(skus)}")
    print(f"Строк итогового отчёта: {len(aggregates)}")
    print(f"Итоговая выручка: {total_revenue}")
    print(f"\nФайл сохранён: {args.output}")

if __name__ == "__main__": main()
