"""prompt_templates.py - Prompt Engineering Patterns for Structured Output.

Demonstrates:
1. XML Tag Delimiters (<instructions>, <schema>, <examples>, <input_text>)
2. Dynamic JSON Schema injection from Pydantic models
3. Few-shot exemplars mapping messy unstructured inputs to clean JSON
4. Error reflection prompt for the retry-on-invalid-output loop
"""

from __future__ import annotations

import json
from typing import Type
from pydantic import BaseModel


def get_extraction_prompt(text: str, schema_class: Type[BaseModel]) -> str:
    """Builds a structured prompt using XML delimiters and JSON Schema."""
    json_schema = json.dumps(schema_class.model_json_schema(), indent=2)

    prompt = f"""<instructions>
You are an expert data extraction assistant.
Extract structured information from the provided unstructured text.
Your response MUST strictly adhere to the provided JSON Schema.
Return ONLY valid raw JSON. Do not include markdown code fences (like ```json), no explanatory text, and no preambles.
</instructions>

<schema>
{json_schema}
</schema>

<examples>
Example 1:
Input: "Paid $42.50 for team lunch at Subway on 10/11/2026. Put it under food."
Output:
{{
  "title": "Team lunch at Subway",
  "amount": 42.5,
  "currency": "USD",
  "category": "Food",
  "date": "2026-11-10"
}}

Example 2:
Input: "Bought software subscription for €19.99 on Nov 5, 2026"
Output:
{{
  "title": "Software subscription",
  "amount": 19.99,
  "currency": "EUR",
  "category": "Tech",
  "date": "2026-11-05"
}}
</examples>

<input_text>
{text}
</input_text>

Output (Raw JSON only):"""
    return prompt.strip()


def get_repair_prompt(
    original_text: str,
    failed_output: str,
    error_feedback: str,
    schema_class: Type[BaseModel],
) -> str:
    """Builds a targeted retry/reflection prompt containing error feedback.

    This prompts the LLM to analyze the exact error and self-correct.
    """
    json_schema = json.dumps(schema_class.model_json_schema(), indent=2)

    prompt = f"""<instructions>
Your previous JSON output was INVALID.
Please review the validation error feedback below, fix ONLY the issues described, and return a corrected, valid JSON object conforming to the target schema.
Do NOT include markdown fences, comments, or introductory text. Output ONLY valid JSON.
</instructions>

<original_input>
{original_text}
</original_input>

<invalid_output>
{failed_output}
</invalid_output>

<validation_errors>
{error_feedback}
</validation_errors>

<target_schema>
{json_schema}
</target_schema>

Corrected Output (Raw JSON only):"""
    return prompt.strip()
