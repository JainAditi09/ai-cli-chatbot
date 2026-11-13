"""schemas.py - Day 2: Structured Output Schemas & Pydantic Validation.

Designed for beginners learning structured LLM extraction for the first time.
Defines clean, easy-to-understand Pydantic models with clear field and model validators:
1. Expense: Extracts financial items from messy receipts, notes, or messages.
2. TaskItem: Extracts action items and to-dos from messy conversations.
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# Common currency symbol mapping
CURRENCY_MAP = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "₹": "INR",
    "¥": "JPY",
    "C$": "CAD",
    "A$": "AUD",
}


class Expense(BaseModel):
    """Simple, clean schema to extract an expense from messy text.

    Example messy input:
    "Had lunch at Chipotle yesterday with Alex, paid $24.50 on card."
    """

    title: str = Field(
        ...,
        description="What was purchased or where (e.g. 'Lunch at Chipotle')",
        min_length=1,
    )
    amount: float = Field(
        ...,
        gt=0,
        description="The monetary cost. Must be a positive number greater than 0.",
    )
    currency: str = Field(
        default="USD",
        description="3-letter currency code (e.g. USD, EUR, INR).",
    )
    category: str = Field(
        default="General",
        description="Category such as Food, Travel, Tech, Supplies, or General.",
    )
    date: str = Field(
        ...,
        description="Date of the expense formatted as YYYY-MM-DD.",
    )

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Title cannot be empty.")
        return cleaned

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        """Converts symbols like '$' to 'USD' and normalizes to uppercase."""
        if not isinstance(v, str):
            raise ValueError("Currency must be a string.")
        cleaned = v.strip().upper()
        # Convert symbol if matched
        if cleaned in CURRENCY_MAP:
            return CURRENCY_MAP[cleaned]
        # Ensure 3 uppercase letters
        if not re.match(r"^[A-Z]{3}$", cleaned):
            raise ValueError(f"Currency '{v}' must be a 3-letter code (e.g. USD, EUR, INR).")
        return cleaned

    @field_validator("category")
    @classmethod
    def format_category(cls, v: str) -> str:
        """Normalizes category to Title Case (e.g., 'food' -> 'Food')."""
        cleaned = v.strip().title()
        return cleaned if cleaned else "General"

    @field_validator("date", mode="before")
    @classmethod
    def normalize_date(cls, v: str) -> str:
        """Parses various date formats and converts to ISO standard YYYY-MM-DD.

        Supports: '2026-11-12', '12/11/2026', 'Nov 12, 2026', '12 Nov 2026', etc.
        """
        if not isinstance(v, str):
            raise ValueError("Date must be a string.")
        cleaned = v.strip()

        # If already YYYY-MM-DD
        if re.match(r"^\d{4}-\d{2}-\d{2}$", cleaned):
            return cleaned

        # Common format attempts
        formats = [
            "%Y/%m/%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%b %d, %Y",
            "%B %d, %Y",
            "%d %b %Y",
            "%d %B %Y",
        ]

        # Strip ordinal suffixes like 1st, 2nd, 3rd, 12th
        clean_ord = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", cleaned)

        for fmt in formats:
            try:
                dt = datetime.strptime(clean_ord, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        raise ValueError(
            f"Invalid date '{v}'. Expected YYYY-MM-DD or standard readable date like 'Nov 12, 2026'."
        )


class TaskItem(BaseModel):
    """Simple schema to extract an action item or to-do from messy notes."""

    title: str = Field(..., min_length=1, description="Description of the task")
    assignee: Optional[str] = Field(default=None, description="Person responsible for the task")
    priority: str = Field(default="Medium", description="Priority: Low, Medium, High")
    due_date: Optional[str] = Field(default=None, description="Due date in YYYY-MM-DD format")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        cleaned = v.strip().capitalize()
        if cleaned not in ("Low", "Medium", "High"):
            raise ValueError(f"Priority must be 'Low', 'Medium', or 'High', got '{v}'")
        return cleaned

