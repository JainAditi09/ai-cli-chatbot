"""repair.py - Deterministic JSON Repair Utilities.

Provides multi-stage sanitization and recovery for malformed JSON strings
frequently emitted by LLMs, including:
- Markdown code fences (```json ... ```)
- Conversational preambles and postambles
- Trailing commas in objects and arrays
- Python literals (True, False, None) -> (true, false, null)
- Unquoted dictionary keys
- JavaScript-style single/multi-line comments
- ast.literal_eval fallback for single-quoted Python dict representations
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any, List, Tuple


def strip_markdown_fences(text: str) -> Tuple[str, bool]:
    """Removes surrounding markdown code blocks (```json ... ```)."""
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip(), True

    # Handle unclosed code blocks at EOF
    unclosed_pattern = r"```(?:json)?\s*([\s\S]*)"
    match_unclosed = re.search(unclosed_pattern, text, re.IGNORECASE)
    if match_unclosed and match_unclosed.group(1).strip() != text.strip():
        return match_unclosed.group(1).strip(), True

    return text.strip(), False


def extract_json_block(text: str) -> Tuple[str, bool]:
    """Extracts the outermost JSON object {...} or array [...] from conversational text."""
    original = text.strip()

    first_brace = original.find("{")
    first_bracket = original.find("[")

    if first_brace == -1 and first_bracket == -1:
        return original, False

    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        last_brace = original.rfind("}")
        if last_brace != -1 and last_brace > first_brace:
            extracted = original[first_brace : last_brace + 1]
            return extracted, extracted != original
    elif first_bracket != -1:
        last_bracket = original.rfind("]")
        if last_bracket != -1 and last_bracket > first_bracket:
            extracted = original[first_bracket : last_bracket + 1]
            return extracted, extracted != original

    return original, False


def strip_json_comments(text: str) -> Tuple[str, bool]:
    """Removes JS/C-style comments (// and /* */) outside of string literals."""
    pattern = r'("(?:\\.|[^"\\])*")|//[^\n]*|/\*[\s\S]*?\*/'

    def replacer(match: re.Match) -> str:
        if match.group(1):
            return match.group(1)
        return ""

    cleaned = re.sub(pattern, replacer, text)
    return cleaned, cleaned != text


def remove_trailing_commas(text: str) -> Tuple[str, bool]:
    """Removes trailing commas before closing braces '}' or brackets ']'."""
    pattern = r'("(?:\\.|[^"\\])*")|,\s*([}\]])'

    def replacer(match: re.Match) -> str:
        if match.group(1):
            return match.group(1)
        return match.group(2)

    cleaned = re.sub(pattern, replacer, text)
    return cleaned, cleaned != text


def normalize_python_literals(text: str) -> Tuple[str, bool]:
    """Converts Python True, False, None to JSON true, false, null outside strings."""
    pattern = r'("(?:\\.|[^"\\])*")|\b(True|False|None)\b'
    replacements = {"True": "true", "False": "false", "None": "null"}

    def replacer(match: re.Match) -> str:
        if match.group(1):
            return match.group(1)
        token = match.group(2)
        return replacements.get(token, token)

    cleaned = re.sub(pattern, replacer, text)
    return cleaned, cleaned != text


def fix_unquoted_keys(text: str) -> Tuple[str, bool]:
    """Wraps unquoted object keys in double quotes: { key: "val" } -> { "key": "val" }."""
    pattern = r'({\s*|,\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:'
    cleaned = re.sub(pattern, r'\1"\2":', text)
    return cleaned, cleaned != text


def repair_json(raw: str) -> Tuple[Any, bool, List[str]]:
    """Attempts to parse raw text as JSON, applying deterministic repairs if needed.

    Returns:
        (parsed_dict_or_list, was_repaired_flag, list_of_repair_actions_applied)

    Raises:
        json.JSONDecodeError or ValueError if text cannot be parsed or repaired.
    """
    raw_stripped = raw.strip()

    # Step 0: Fast path for already valid JSON
    try:
        data = json.loads(raw_stripped)
        return data, False, []
    except (json.JSONDecodeError, ValueError):
        pass

    actions: List[str] = []
    current = raw_stripped

    # Step 1: Strip markdown fences
    current, changed = strip_markdown_fences(current)
    if changed:
        actions.append("stripped_markdown_fences")
        try:
            return json.loads(current), True, actions
        except (json.JSONDecodeError, ValueError):
            pass

    # Step 2: Extract JSON block from conversational text
    current, changed = extract_json_block(current)
    if changed:
        actions.append("extracted_outer_json_block")
        try:
            return json.loads(current), True, actions
        except (json.JSONDecodeError, ValueError):
            pass

    # Step 3: Strip comments
    current, changed = strip_json_comments(current)
    if changed:
        actions.append("stripped_comments")
        try:
            return json.loads(current), True, actions
        except (json.JSONDecodeError, ValueError):
            pass

    # Step 4: Normalize Python literals (True/False/None)
    current, changed = normalize_python_literals(current)
    if changed:
        actions.append("normalized_python_literals")
        try:
            return json.loads(current), True, actions
        except (json.JSONDecodeError, ValueError):
            pass

    # Step 5: Remove trailing commas
    current, changed = remove_trailing_commas(current)
    if changed:
        actions.append("removed_trailing_commas")
        try:
            return json.loads(current), True, actions
        except (json.JSONDecodeError, ValueError):
            pass

    # Step 6: Fix unquoted keys
    current, changed = fix_unquoted_keys(current)
    if changed:
        actions.append("quoted_unquoted_keys")
        try:
            return json.loads(current), True, actions
        except (json.JSONDecodeError, ValueError):
            pass

    # Step 7: ast.literal_eval fallback (for single-quoted Python dict representations)
    try:
        evaluated = ast.literal_eval(current)
        if isinstance(evaluated, (dict, list)):
            actions.append("python_ast_literal_eval_fallback")
            sanitized = json.loads(json.dumps(evaluated))
            return sanitized, True, actions
    except Exception:
        pass

    # Final attempt: will raise standard JSONDecodeError with line/col details
    data = json.loads(current)
    return data, True, actions
