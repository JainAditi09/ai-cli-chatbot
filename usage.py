from config import (
    INPUT_PRICE_PER_1M,
    OUTPUT_PRICE_PER_1M
)

total_input_tokens = 0
total_output_tokens = 0
total_cost = 0.0


def track_usage(input_tokens, output_tokens):
    global total_input_tokens
    global total_output_tokens
    global total_cost

    request_cost = (
        input_tokens * INPUT_PRICE_PER_1M / 1_000_000
        + output_tokens * OUTPUT_PRICE_PER_1M / 1_000_000
    )

    total_input_tokens += input_tokens
    total_output_tokens += output_tokens
    total_cost += request_cost

    print("\n\n--- Request Usage ---")
    print(f"Input tokens: {input_tokens}")
    print(f"Output tokens: {output_tokens}")
    print(f"Request cost: ${request_cost:.8f}")

    show_usage()


def show_usage():
    print("\n--- Session Usage ---")
    print(f"Input tokens: {total_input_tokens}")
    print(f"Output tokens: {total_output_tokens}")
    print(f"Total cost: ${total_cost:.8f}")