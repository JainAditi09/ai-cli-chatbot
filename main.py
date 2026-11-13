import json
from chatbot import ask_ai
from history import reset_history, show_history
from usage import show_usage
from extractor import MessyTextExtractor
from schemas import Expense


def handle_extract():
    """Interactive handler for Day 2 structured output extraction."""
    print("\n" + "-" * 45)
    print("  DAY 2: STRUCTURED DATA EXTRACTOR")
    print("-" * 45)
    print("Paste unstructured messy text (e.g. receipt, note, or expense):")
    print("Example: 'Paid $18.50 for airport taxi on 12/11/2026, travel expense'")

    try:
        raw_text = input("\nMessy Text > ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExtraction cancelled.")
        return

    if not raw_text:
        print("No text provided. Returning to main chat.")
        return

    print("\nSending prompt to Gemini API (gemini-3.8-flash)...")
    extractor = MessyTextExtractor()
    result = extractor.extract(raw_text, schema_class=Expense)

    if result.success and result.data:
        print("\n✅ Extraction Successful!")
        print(f"Attempts needed: {result.attempts}")
        if result.repaired_locally:
            print(f"🛠️ Repaired locally: Yes ({', '.join(result.repair_actions)})")
        print("\nValidated Pydantic Object:")
        print(json.dumps(result.data.model_dump(), indent=2))
    else:
        print("\n❌ Extraction Failed after retries:")
        for err in result.errors:
            print(f"  - {err}")


def main():
    print("=" * 45)
    print("       GEMINI PYTHON CLI CHATBOT")
    print("=" * 45)

    print("""
Commands:
  /history  - Show conversation history
  /reset    - Clear conversation history
  /usage    - Show token and cost usage
  /extract  - Extract structured data from messy text (Day 2)
  /exit     - Exit chatbot
""")

    while True:
        try:
            question = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not question:
            continue

        if question == "/exit":
            print("Goodbye!")
            break

        elif question == "/history":
            show_history()

        elif question == "/reset":
            reset_history()
            print("Conversation history cleared.")

        elif question == "/usage":
            show_usage()

        elif question == "/extract":
            handle_extract()

        else:
            ask_ai(question)


if __name__ == "__main__":
    main()
