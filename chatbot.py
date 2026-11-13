import time
from history import get_chat
from usage import track_usage


def ask_ai(question, max_retries=3):
    chat = get_chat()

    for attempt in range(1, max_retries + 1):
        assistant_response = ""
        input_tokens = 0
        output_tokens = 0
        usage_received = False

        try:
            print("\nAI: ", end="", flush=True)
            stream = chat.send_message_stream(message=question)

            for chunk in stream:
                if chunk.text:
                    print(chunk.text, end="", flush=True)
                    assistant_response += chunk.text

                metadata = chunk.usage_metadata
                if metadata:
                    input_tokens = metadata.prompt_token_count or 0
                    output_tokens = metadata.candidates_token_count or 0
                    usage_received = True

            print()

            if usage_received:
                track_usage(input_tokens, output_tokens)
            else:
                print("Token usage metadata was not returned.")
            
            # Request succeeded, exit retry loop
            return

        except Exception as error:
            error_str = str(error)
            is_transient = any(
                code in error_str
                for code in ("503", "429", "UNAVAILABLE", "ResourceExhausted", "high demand")
            )
            # If Google servers are busy (503/429), wait and retry
            if is_transient and attempt < max_retries:
                wait_time = attempt * 2  # 2s, then 4s
                print(
                    f"\n[Gemini servers busy/rate-limited. Retrying in {wait_time}s... (Attempt {attempt}/{max_retries})]"
                )
                time.sleep(wait_time)
                continue
            else:
                print(f"\nGemini API error: {error}")
                return