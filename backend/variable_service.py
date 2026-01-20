"""
Variable interpolation service for Story Engine.
Handles stepN_output variable detection and expansion.
"""

import re
from typing import Dict, List


def expand_variables(text: str, outputs: Dict[str, str]) -> str:
    """Replace stepN_output placeholders with actual values.

    Args:
        text: Text containing variable placeholders
        outputs: Dict mapping variable names to their values
                e.g., {"step0_output": "...", "step1_output": "..."}

    Returns:
        Text with placeholders replaced by actual values
    """
    pattern = r'\b(step\d+_output)\b'

    def replace_match(match):
        var_name = match.group(1)
        value = outputs.get(var_name, "")
        return value if value else f"[{var_name} not yet generated]"

    return re.sub(pattern, replace_match, text)


def get_detected_variables(text: str) -> List[str]:
    """Return list of variable names found in the text.

    Args:
        text: Text to search for variables

    Returns:
        List of unique variable names found (e.g., ["step0_output", "step1_output"])
    """
    pattern = r'\b(step\d+_output)\b'
    return list(set(re.findall(pattern, text)))


def has_variables(text: str) -> bool:
    """Check if text contains any variable placeholders.

    Args:
        text: Text to check

    Returns:
        True if text contains stepN_output patterns
    """
    pattern = r'\bstep\d+_output\b'
    return bool(re.search(pattern, text))


def get_available_variables(current_step: int, outputs: Dict[str, str]) -> List[str]:
    """Get list of available variable names based on generated outputs.

    Args:
        current_step: The current step number (0, 1, or 2)
        outputs: Dict of all outputs

    Returns:
        List of variable names that have been generated and are available for use
    """
    variables = []
    for i in range(current_step):
        var_name = f"step{i}_output"
        if outputs.get(var_name):
            variables.append(var_name)
    return variables


def validate_variables(text: str, outputs: Dict[str, str]) -> Dict[str, List[str]]:
    """Validate variables in text and categorize them.

    Args:
        text: Text containing variable placeholders
        outputs: Dict of available outputs

    Returns:
        Dict with 'valid' and 'pending' lists of variable names
    """
    detected = get_detected_variables(text)
    valid = [v for v in detected if outputs.get(v)]
    pending = [v for v in detected if not outputs.get(v)]

    return {
        "valid": valid,
        "pending": pending
    }
