"""extractor.py - Messy-Text Extractor with Local Repair & Retry Loop.

A beginner-friendly structured data extractor that turns messy text into
validated Pydantic objects using a multi-layer defense:

Layer 1: Prompt engineering with XML tags & dynamic JSON Schema
Layer 2: Local deterministic repair (strips markdown fences, quotes, trailing commas)
Layer 3: Pydantic validation (field constraints & normalizations)
Layer 4: Self-correction retry loop (feeds validation errors back to LLM)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from typing import Any, Callable, Generic, List, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from config import API_KEY, MODEL
from prompt_templates import get_extraction_prompt, get_repair_prompt
from repair import repair_json
from schemas import Expense

T = TypeVar("T", bound=BaseModel)


@dataclass
class ExtractionResult(Generic[T]):
    """Container for the extraction outcome and diagnostic metadata."""

    data: Optional[T] = None
    success: bool = False
    attempts: int = 1
    repaired_locally: bool = False
    repair_actions: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    raw_response: str = ""


class MessyTextExtractor:
    """Extracts validated Pydantic models from unstructured text with self-healing retries."""

    def __init__(
        self,
        client: Any = None,
        model: str = MODEL,
        max_retries: int = 3,
        generator_func: Optional[Callable[[str], str]] = None,
    ):
        """Initializes the extractor.

        Args:
            client: Optional google.genai.Client instance.
            model: Gemini model identifier.
            max_retries: Maximum number of generation attempts (1 initial + retries).
            generator_func: Optional custom text generation function (useful for tests and mocking).
        """
        self.model = model
        self.max_retries = max(1, max_retries)
        self.generator_func = generator_func

        if generator_func is None:
            if client is not None:
                self.client = client
            else:
                from google import genai

                self.client = genai.Client(api_key=API_KEY)
        else:
            self.client = None

    def _call_model(self, prompt: str, transient_retries: int = 3) -> str:
        """Invokes the LLM or custom generator function with backoff for transient server errors (503/429)."""
        if self.generator_func is not None:
            return self.generator_func(prompt)

        for attempt in range(1, transient_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                return response.text or ""
            except Exception as e:
                err_str = str(e)
                # Catch 503 UNAVAILABLE, 429 RESOURCE_EXHAUSTED, or high-demand spikes
                is_transient = any(
                    code in err_str
                    for code in ("503", "429", "UNAVAILABLE", "ResourceExhausted", "high demand")
                )
                if is_transient and attempt < transient_retries:
                    wait_time = attempt * 2  # 2s, 4s
                    time.sleep(wait_time)
                    continue
                raise e

    def extract(
        self,
        text: str,
        schema_class: Type[T] = Expense,
    ) -> ExtractionResult[T]:
        """Extracts and validates structured data from unstructured text.

        Args:
            text: Raw, messy input string.
            schema_class: Target Pydantic model class (defaults to Expense).

        Returns:
            ExtractionResult containing the validated model or diagnostic error details.
        """
        errors_history: List[str] = []
        last_raw_response = ""
        last_repair_actions: List[str] = []
        last_repaired_flag = False

        for attempt in range(1, self.max_retries + 1):
            # Step 1: Formulate prompt
            if attempt == 1:
                prompt = get_extraction_prompt(text, schema_class)
            else:
                # Feedback loop: Pass exact error details back to the LLM
                prompt = get_repair_prompt(
                    original_text=text,
                    failed_output=last_raw_response,
                    error_feedback="\n".join(errors_history),
                    schema_class=schema_class,
                )

            # Step 2: Generate response from LLM
            try:
                raw_response = self._call_model(prompt)
                last_raw_response = raw_response
            except Exception as e:
                error_msg = f"LLM generation error on attempt {attempt}: {str(e)}"
                errors_history.append(error_msg)
                continue

            # Step 3: Local deterministic JSON repair
            parsed_data: Any = None
            try:
                parsed_data, was_repaired, actions = repair_json(raw_response)
                last_repaired_flag = was_repaired
                last_repair_actions = actions
            except (json.JSONDecodeError, ValueError) as err:
                error_msg = f"JSON syntax error on attempt {attempt}: {str(err)}"
                errors_history.append(error_msg)
                continue

            # Ensure parsed data is a dictionary
            if not isinstance(parsed_data, dict):
                error_msg = (
                    f"Attempt {attempt} returned JSON {type(parsed_data).__name__}, "
                    "expected a JSON object/dictionary."
                )
                errors_history.append(error_msg)
                continue

            # Step 4: Validate against Pydantic schema
            try:
                validated_model = schema_class.model_validate(parsed_data)
                return ExtractionResult(
                    data=validated_model,
                    success=True,
                    attempts=attempt,
                    repaired_locally=last_repaired_flag,
                    repair_actions=last_repair_actions,
                    errors=errors_history,
                    raw_response=last_raw_response,
                )
            except ValidationError as val_err:
                # Format friendly validation feedback for next attempt
                field_errors = []
                for err in val_err.errors():
                    loc = " -> ".join(str(p) for p in err.get("loc", []))
                    msg = err.get("msg", "Validation failed")
                    field_errors.append(f"- Field '{loc}': {msg}")
                error_msg = f"Schema validation error on attempt {attempt}:\n" + "\n".join(
                    field_errors
                )
                errors_history.append(error_msg)

        # Retries exhausted
        return ExtractionResult(
            data=None,
            success=False,
            attempts=self.max_retries,
            repaired_locally=last_repaired_flag,
            repair_actions=last_repair_actions,
            errors=errors_history,
            raw_response=last_raw_response,
        )
