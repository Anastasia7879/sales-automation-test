import csv 
import sys 
import unittest 
import tempfile 
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import calculate, write_report

class SalesAggregationTests(unittest.TestCase):
    def make_csv(self, content):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        path = Path(temp.name) / "sales.csv"
        path.write_text(content, encoding="utf-8")

        return path

    def test_duplicates_and_cancelled_orders(self):
        """Проверяем дубли и отменённые заказы."""

        path = self.make_csv(
            "order_id,order_date,sku,quantity,price,status\n"
            "1,2026-01-01,A,2,10,delivered\n"
            "1,2026-01-01,A,2,10,delivered\n"
            "2,2026-01-01,A,,10,canceled\n"
        )

        result = calculate(path)

        self.assertEqual(
            result[("A", "2026-01-01")],
            [2, 20]
        )

    def test_conflicting_duplicate(self):
        """Проверяем обнаружение конфликтующих дублей."""

        path = self.make_csv(
            "order_id,order_date,sku,quantity,price,status\n"
            "1,2026-01-01,A,1,10,delivered\n"
            "1,2026-01-02,A,1,10,delivered\n"
        )

        with self.assertRaisesRegex(
            ValueError, "разными данными"
        ):
            calculate(path)

    def test_missing_quantity(self):
        """Проверяем пропуск количества у выкупленного заказа."""

        path = self.make_csv(
            "order_id,order_date,sku,quantity,price,status\n"
            "1,2026-01-01,A,,10,delivered\n"
        )

        with self.assertRaisesRegex(
            ValueError, "отсутствует quantity"
        ):
            calculate(path)

    def test_output_sorting(self):
        """Проверяем сортировку итоговой таблицы."""

        path = self.make_csv(
            "order_id,order_date,sku,quantity,price,status\n"
            "1,2026-01-02,B,1,10,delivered\n"
            "2,2026-01-01,A,1,20,delivered\n"
        )

        result = calculate(path)

        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "result.csv"

            write_report(result, output)

            with output.open(
                encoding="utf-8", newline=""
            ) as stream:
                rows = list(csv.reader(stream))

            self.assertEqual(
                rows[1][0:2],
                ["A", "2026-01-01"]
            )

            self.assertEqual(
                rows[2][0:2],
                ["B", "2026-01-02"]
            )
if __name__ == "__main__": 
    unittest.main(verbosity=2)