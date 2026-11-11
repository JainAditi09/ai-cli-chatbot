from chatbot import ask_ai
from history import reset_history, show_history
from usage import show_usage


def main():
    print("=" * 45)
    print("       GEMINI PYTHON CLI CHATBOT")
    print("=" * 45)

    print("""
Commands:
  /history  - Show conversation history
  /reset    - Clear conversation history
  /usage    - Show token and cost usage
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

        else:
            ask_ai(question)


if __name__ == "__main__":
    main()