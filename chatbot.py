from history import get_chat
from usage import track_usage


def ask_ai(question):
    chat = get_chat()

    assistant_response = ""

    input_tokens = 0
    output_tokens = 0
    usage_received = False

    print("\nAI: ", end="", flush=True)

    try:
        stream = chat.send_message_stream(message=question)

        for chunk in stream:

            # Display generated text immediately
            if chunk.text:
                print(chunk.text, end="", flush=True)
                assistant_response += chunk.text

            # Capture the latest usage metadata
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

    except Exception as error:
        print(f"\nGemini API error: {error}")