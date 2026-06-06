import re


MATH_CHARS = set("0123456789+-*/^=().xxyz ")


def looks_like_math(text: str) -> bool:
    stripped = text.replace(" ", "")
    if not stripped:
        return False
    # if most chars are mathy, call it math
    math_count = sum(1 for c in stripped if c in MATH_CHARS)
    return math_count / len(stripped) > 0.6


def extract_equation(text: str) -> str:
    # naive: take longest substring containing '='
    if "=" in text:
        return text[text.index("=") - 20:text.index("=") + 20].strip()
    return text.strip()
