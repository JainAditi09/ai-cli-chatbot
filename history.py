from google import genai
from google.genai import types

from config import API_KEY, MODEL

client = genai.Client(api_key=API_KEY)

SYSTEM_PROMPT = """
You are a helpful AI assistant.
Explain concepts in simple language with practical examples.
"""


def create_chat():
    return client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT
        )
    )


chat = create_chat()


def get_chat():
    return chat


def show_history():
    history = chat.get_history()

    if not history:
        print("No conversation history yet.")
        return

    # Group consecutive messages with the same role (aggregating streamed chunks)
    turns = []
    current_role = None
    current_text = []

    for message in history:
        role = (message.role or "unknown").upper()
        if role == "MODEL":
            role = "AI"

        text_parts = []
        if message.parts:
            for part in message.parts:
                # Exclude internal reasoning/thought parts
                if getattr(part, "thought", False):
                    continue
                if getattr(part, "text", None):
                    text_parts.append(part.text)

        message_text = "".join(text_parts)
        if not message_text:
            continue

        if role == current_role:
            current_text.append(message_text)
        else:
            if current_role is not None and current_text:
                turns.append((current_role, "".join(current_text).strip()))
            current_role = role
            current_text = [message_text]

    if current_role is not None and current_text:
        turns.append((current_role, "".join(current_text).strip()))

    if not turns:
        print("No conversation history yet.")
        return

    for role, text in turns:
        print(f"\n{role}: {text}")


def reset_history():
    global chat
    chat = create_chat()