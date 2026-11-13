"""demo_day2.py - Interactive Beginner Walkthrough for Day 2.

Run this script to understand:
1. Pydantic schema validation (schemas.py)
2. Deterministic local JSON repair (repair.py)
3. Self-healing retry loops with simulated and live LLMs (extractor.py)
"""

from __future__ import annotations

import json
from extractor import MessyTextExtractor
from repair import repair_json
from schemas import Expense


def section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def demo_pydantic_validation():
    section("1. Pydantic Schema Validation & Normalization")
    print("Notice how Pydantic automatically normalizes '$' -> 'USD' and dates -> 'YYYY-MM-DD':")

    expense = Expense(
        title="Team coffee & donuts",
        amount=14.50,
        currency="$",
        category="food",
        date="Nov 12, 2026",
    )
    print("\nValidated Pydantic model:")
    print(json.dumps(expense.model_dump(), indent=2))


def demo_deterministic_repair():
    section("2. Deterministic JSON Repair (Zero API Cost)")
    print("LLMs frequently return markdown fences, trailing commas, or single quotes.")
    print("Our repair engine fixes these instantly without extra LLM token charges!\n")

    messy_llm_output = """```json
    {
      'title': 'Uber to airport',
      'amount': 38.25,
      'currency': '$',
      'category': 'Travel',
      'date': '2026-11-12',
    }
    ```"""

    print("Raw LLM Output:")
    print(messy_llm_output)

    repaired_dict, was_repaired, actions = repair_json(messy_llm_output)
    print("\nLocal Repair Result:")
    print(f"Repaired: {was_repaired}")
    print(f"Actions taken: {actions}")
    print(f"Parsed Python dict: {repaired_dict}")

    validated = Expense.model_validate(repaired_dict)
    print(f"\nFinal Validated Expense: {validated.title} -> {validated.amount} {validated.currency}")


def demo_simulated_retry_loop():
    section("3. Self-Healing Retry Loop (Simulating Error Correction)")
    print("What happens when an LLM outputs logically invalid data (e.g. negative cost)?")
    print("The extractor catches the Pydantic ValidationError and sends targeted feedback.\n")

    # Mock generator: fails attempt 1 with negative amount, succeeds attempt 2
    mock_responses = [
        '{"title": "Office Supplies", "amount": -25.0, "currency": "USD", "category": "Supplies", "date": "2026-11-12"}',
        '{"title": "Office Supplies", "amount": 25.0, "currency": "USD", "category": "Supplies", "date": "2026-11-12"}',
    ]

    def mock_generator(prompt: str) -> str:
        resp = mock_responses.pop(0)
        print(f"[Mock LLM Output]: {resp}")
        return resp

    extractor = MessyTextExtractor(generator_func=mock_generator, max_retries=3)
    result = extractor.extract(
        text="Bought $25 pens for office",
        schema_class=Expense,
    )

    print("\nResult:")
    print(f"Success: {result.success}")
    print(f"Total attempts needed: {result.attempts}")
    print(f"Errors captured on earlier attempts: {result.errors}")
    print(f"Final Data: {result.data}")


def demo_live_extraction():
    section("4. Live Extraction via Gemini API")
    sample_text = "Grabbed dinner with Priya at Olive Garden yesterday, total bill was $45.80 paid with card. Mark as food."
    print(f"Input text:\n\"{sample_text}\"\n")

    try:
        extractor = MessyTextExtractor(max_retries=3)
        print("Calling Gemini API...")
        result = extractor.extract(sample_text, schema_class=Expense)

        if result.success and result.data:
            print("✅ Successfully extracted:")
            print(json.dumps(result.data.model_dump(), indent=2))
            print(f"Attempts: {result.attempts}, Repaired locally: {result.repaired_locally}")
        else:
            print("❌ Extraction failed:")
            for err in result.errors:
                print(f"  - {err}")
    except Exception as e:
        print(f"Live API call skipped or failed: {e}")


if __name__ == "__main__":
    demo_pydantic_validation()
    demo_deterministic_repair()
    demo_simulated_retry_loop()
    demo_live_extraction()
