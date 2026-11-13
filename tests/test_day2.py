"""tests/test_day2.py - Comprehensive Unit Tests for Day 2 Deliverables.

Covers:
1. Pydantic schema validation & custom field validators
2. Deterministic JSON repair (markdown fences, trailing commas, single quotes, etc.)
3. Self-healing retry-on-invalid-output loop (syntax errors, validation errors, retry limits)
"""

from __future__ import annotations

import unittest
from pydantic import ValidationError

from extractor import MessyTextExtractor
from prompt_templates import get_extraction_prompt, get_repair_prompt
from repair import (
    extract_json_block,
    normalize_python_literals,
    remove_trailing_commas,
    repair_json,
    strip_json_comments,
    strip_markdown_fences,
)
from schemas import Expense, TaskItem


class TestSchemasAndValidators(unittest.TestCase):
    """Tests for Pydantic models and field validators."""

    def test_valid_expense_creation(self):
        """Valid data should create an Expense and normalize fields."""
        expense = Expense(
            title="Team Lunch",
            amount=35.50,
            currency="$",
            category="food",
            date="Nov 12, 2026",
        )
        self.assertEqual(expense.title, "Team Lunch")
        self.assertEqual(expense.amount, 35.50)
        self.assertEqual(expense.currency, "USD")
        self.assertEqual(expense.category, "Food")
        self.assertEqual(expense.date, "2026-11-12")

    def test_currency_symbol_normalization(self):
        """Common currency symbols should map to 3-letter ISO codes."""
        symbols_to_iso = {
            "$": "USD",
            "€": "EUR",
            "£": "GBP",
            "₹": "INR",
            "¥": "JPY",
        }
        for sym, iso in symbols_to_iso.items():
            exp = Expense(
                title="Item",
                amount=10.0,
                currency=sym,
                date="2026-11-12",
            )
            self.assertEqual(exp.currency, iso)

    def test_date_format_normalization(self):
        """Various human and standard date formats should normalize to YYYY-MM-DD."""
        test_dates = [
            ("2026-11-12", "2026-11-12"),
            ("11/12/2026", "2026-11-12"),
            ("25/11/2026", "2026-11-25"),
            ("Nov 12, 2026", "2026-11-12"),
            ("12 Nov 2026", "2026-11-12"),
            ("November 12th, 2026", "2026-11-12"),
        ]
        for raw_date, expected_iso in test_dates:
            exp = Expense(
                title="Date Test",
                amount=10.0,
                date=raw_date,
            )
            self.assertEqual(exp.date, expected_iso)

    def test_invalid_amount_rejected(self):
        """Amounts <= 0 should raise a ValidationError."""
        with self.assertRaises(ValidationError):
            Expense(title="Free item", amount=0.0, date="2026-11-12")

        with self.assertRaises(ValidationError):
            Expense(title="Negative item", amount=-15.0, date="2026-11-12")

    def test_empty_title_rejected(self):
        """Empty or whitespace-only titles should raise a ValidationError."""
        with self.assertRaises(ValidationError):
            Expense(title="   ", amount=10.0, date="2026-11-12")

    def test_invalid_date_rejected(self):
        """Unparseable dates should raise a ValidationError."""
        with self.assertRaises(ValidationError):
            Expense(title="Item", amount=10.0, date="not-a-real-date")

    def test_task_item_priority_validation(self):
        """TaskItem should validate priority enum values."""
        task = TaskItem(title="Submit PR", priority="high")
        self.assertEqual(task.priority, "High")

        with self.assertRaises(ValidationError):
            TaskItem(title="Submit PR", priority="urgent_now")


class TestDeterministicJSONRepair(unittest.TestCase):
    """Tests for deterministic JSON sanitization without extra API costs."""

    def test_strip_markdown_fences(self):
        raw = "```json\n{\"title\": \"Lunch\", \"amount\": 15.0}\n```"
        stripped, changed = strip_markdown_fences(raw)
        self.assertTrue(changed)
        self.assertNotIn("```", stripped)

    def test_extract_outer_json_block(self):
        raw = "Hello! Here is the JSON:\n{\"title\": \"Coffee\", \"amount\": 4.5}\nHope this helps!"
        extracted, changed = extract_json_block(raw)
        self.assertTrue(changed)
        self.assertEqual(extracted, '{"title": "Coffee", "amount": 4.5}')

    def test_remove_trailing_commas(self):
        raw = '{"items": [1, 2, ], "total": 10, }'
        cleaned, changed = remove_trailing_commas(raw)
        self.assertTrue(changed)
        self.assertEqual(cleaned, '{"items": [1, 2], "total": 10}')

    def test_normalize_python_literals(self):
        raw = '{"active": True, "archived": False, "note": None}'
        cleaned, changed = normalize_python_literals(raw)
        self.assertTrue(changed)
        self.assertEqual(cleaned, '{"active": true, "archived": false, "note": null}')

    def test_strip_json_comments(self):
        raw = '{\n  // single line comment\n  "amount": 20.0 /* inline comment */\n}'
        cleaned, changed = strip_json_comments(raw)
        self.assertTrue(changed)
        self.assertNotIn("//", cleaned)
        self.assertNotIn("/*", cleaned)

    def test_repair_json_full_pipeline(self):
        """Messy combined output should be fully repaired into a valid dict."""
        messy_llm_output = """Here is the result:
```json
{
  'title': 'Dinner with team',
  'amount': 85.50,
  'currency': '$',
  'category': 'Food',
  'date': '2026-11-12',
}
```"""
        data, was_repaired, actions = repair_json(messy_llm_output)
        self.assertTrue(was_repaired)
        self.assertIsInstance(data, dict)
        self.assertEqual(data["title"], "Dinner with team")
        self.assertEqual(data["amount"], 85.50)
        self.assertEqual(data["currency"], "$")


class TestRetryOnInvalidOutput(unittest.TestCase):
    """Tests for the self-healing retry loop when LLMs return invalid output."""

    def test_immediate_success(self):
        """When LLM returns valid JSON on attempt 1, no retries are triggered."""
        generator = lambda prompt: '{"title": "Taxi", "amount": 20.0, "currency": "USD", "category": "Travel", "date": "2026-11-12"}'
        extractor = MessyTextExtractor(generator_func=generator, max_retries=3)

        result = extractor.extract("Taxi $20", schema_class=Expense)
        self.assertTrue(result.success)
        self.assertEqual(result.attempts, 1)
        self.assertIsNotNone(result.data)
        self.assertEqual(result.data.title, "Taxi")

    def test_retry_heals_syntax_error(self):
        """Attempt 1 returns broken syntax; Attempt 2 returns valid JSON."""
        responses = [
            "This is not JSON at all!",  # Attempt 1 fails JSON parse
            '{"title": "Groceries", "amount": 45.0, "currency": "USD", "category": "Food", "date": "2026-11-12"}',
        ]
        generator = lambda prompt: responses.pop(0)
        extractor = MessyTextExtractor(generator_func=generator, max_retries=3)

        result = extractor.extract("Groceries $45", schema_class=Expense)
        self.assertTrue(result.success)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("JSON syntax error", result.errors[0])
        self.assertEqual(result.data.title, "Groceries")

    def test_retry_heals_validation_error(self):
        """Attempt 1 returns negative amount; feedback triggers fixed amount in Attempt 2."""
        prompts_received = []
        responses = [
            # Attempt 1: invalid negative amount
            '{"title": "Subway", "amount": -8.50, "currency": "USD", "category": "Food", "date": "2026-11-12"}',
            # Attempt 2: corrected positive amount
            '{"title": "Subway", "amount": 8.50, "currency": "USD", "category": "Food", "date": "2026-11-12"}',
        ]

        def tracking_generator(prompt: str) -> str:
            prompts_received.append(prompt)
            return responses.pop(0)

        extractor = MessyTextExtractor(generator_func=tracking_generator, max_retries=3)
        result = extractor.extract("Subway $8.50", schema_class=Expense)

        self.assertTrue(result.success)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(result.data.amount, 8.50)
        # Verify the repair prompt included the validation error feedback
        self.assertIn("<validation_errors>", prompts_received[1])
        self.assertIn("greater than 0", prompts_received[1])

    def test_retry_heals_missing_required_fields(self):
        """Attempt 1 misses 'date' and 'amount'; Attempt 2 provides complete object."""
        responses = [
            '{"title": "Airport Bus"}',  # Missing amount and date
            '{"title": "Airport Bus", "amount": 12.0, "currency": "USD", "category": "Travel", "date": "2026-11-12"}',
        ]
        generator = lambda prompt: responses.pop(0)
        extractor = MessyTextExtractor(generator_func=generator, max_retries=3)

        result = extractor.extract("Airport Bus $12", schema_class=Expense)
        self.assertTrue(result.success)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(result.data.amount, 12.0)
        self.assertEqual(result.data.date, "2026-11-12")

    def test_non_dict_json_handled_with_retry(self):
        """LLM returns a JSON array instead of an object; retry corrects it."""
        responses = [
            '["not", "an", "object"]',
            '{"title": "Notebook", "amount": 5.0, "currency": "USD", "category": "Supplies", "date": "2026-11-12"}',
        ]
        generator = lambda prompt: responses.pop(0)
        extractor = MessyTextExtractor(generator_func=generator, max_retries=3)

        result = extractor.extract("Notebook $5", schema_class=Expense)
        self.assertTrue(result.success)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(result.data.title, "Notebook")

    def test_unquoted_keys_repaired_locally(self):
        """Unquoted keys like { title: 'Coffee' } should be repaired without retry."""
        generator = lambda prompt: '{ title: "Coffee", amount: 4.5, currency: "USD", category: "Food", date: "2026-11-12" }'
        extractor = MessyTextExtractor(generator_func=generator, max_retries=2)

        result = extractor.extract("Coffee $4.50", schema_class=Expense)
        self.assertTrue(result.success)
        self.assertEqual(result.attempts, 1)
        self.assertTrue(result.repaired_locally)
        self.assertIn("quoted_unquoted_keys", result.repair_actions)

    def test_retries_exhausted(self):
        """If all attempts fail, returns success=False and logs all errors."""
        generator = lambda prompt: "Still invalid JSON {{"
        extractor = MessyTextExtractor(generator_func=generator, max_retries=2)

        result = extractor.extract("Messy input", schema_class=Expense)
        self.assertFalse(result.success)
        self.assertEqual(result.attempts, 2)
        self.assertIsNone(result.data)
        self.assertEqual(len(result.errors), 2)


if __name__ == "__main__":
    unittest.main()
