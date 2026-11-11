import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

INPUT_PRICE_PER_1M = float(
    os.getenv("INPUT_PRICE_PER_1M", "0")
)

OUTPUT_PRICE_PER_1M = float(
    os.getenv("OUTPUT_PRICE_PER_1M", "0")
)

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env")